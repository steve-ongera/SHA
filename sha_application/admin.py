from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    User, County, SubCounty, SHAMember, MemberDocument, Employer, EmployerMember,
    Hospital, HospitalStaff, Contribution, OTP, HospitalVisit, Medicine, PharmacyStock,
    Prescription, PrescriptionItem, Claim, Notification, AuditLog, GovernmentReport
)

# ============================================================================
# CUSTOM USER ADMIN
# ============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'user_type', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_verified', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'phone_number']
    readonly_fields = ['date_joined', 'last_login']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone_number', 'is_verified')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

# ============================================================================
# LOCATION MODELS
# ============================================================================

@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'subcounty_count']
    search_fields = ['name', 'code']
    ordering = ['name']
    
    def subcounty_count(self, obj):
        return obj.subcounties.count()
    subcounty_count.short_description = 'Sub-Counties'

@admin.register(SubCounty)
class SubCountyAdmin(admin.ModelAdmin):
    list_display = ['name', 'county', 'code']
    list_filter = ['county']
    search_fields = ['name', 'county__name']
    ordering = ['county__name', 'name']

# ============================================================================
# MEMBER ADMIN
# ============================================================================

class MemberDocumentInline(admin.TabularInline):
    model = MemberDocument
    extra = 0
    readonly_fields = ['uploaded_at', 'verified_by']
    fields = ['document_type', 'document_file', 'description', 'verified', 'verified_by', 'uploaded_at']

@admin.register(SHAMember)
class SHAMemberAdmin(admin.ModelAdmin):
    list_display = [
        'sha_number', 'full_name', 'id_number', 'status', 
        'county', 'registration_date', 'contribution_status'
    ]
    list_filter = [
        'status', 'county', 'gender', 'registration_date', 'approval_date'
    ]
    search_fields = [
        'sha_number', 'first_name', 'last_name', 'id_number', 
        'phone_number', 'email'
    ]
    readonly_fields = [
        'sha_number', 'registration_date', 'approved_by', 'qr_code_preview'
    ]
    date_hierarchy = 'registration_date'
    inlines = [MemberDocumentInline]
    
    fieldsets = (
        ('SHA Information', {
            'fields': ('sha_number', 'status', 'registration_date', 'approval_date', 'approved_by')
        }),
        ('Personal Information', {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
                ('id_number', 'date_of_birth', 'gender'),
            )
        }),
        ('Contact Information', {
            'fields': (
                ('phone_number', 'email'),
                'postal_address', 'physical_address',
                ('county', 'subcounty')
            )
        }),
        ('Biometric Data', {
            'fields': ('photo', 'fingerprint_template', 'qr_code', 'qr_code_preview'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_members', 'suspend_members', 'activate_members']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.qr_code.url
            )
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code Preview'
    
    def contribution_status(self, obj):
        current_month = timezone.now().date().replace(day=1)
        has_contributed = obj.contributions.filter(
            contribution_month=current_month,
            status='completed'
        ).exists()
        
        if has_contributed:
            return format_html('<span style="color: green;">✓ Paid</span>')
        else:
            return format_html('<span style="color: red;">✗ Pending</span>')
    contribution_status.short_description = 'Current Month'
    
    def approve_members(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='active',
            approval_date=timezone.now(),
            approved_by=request.user
        )
        self.message_user(request, f'{updated} members approved successfully.')
    approve_members.short_description = 'Approve selected members'
    
    def suspend_members(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} members suspended.')
    suspend_members.short_description = 'Suspend selected members'
    
    def activate_members(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} members activated.')
    activate_members.short_description = 'Activate selected members'

@admin.register(MemberDocument)
class MemberDocumentAdmin(admin.ModelAdmin):
    list_display = ['member', 'document_type', 'verified', 'uploaded_at', 'verified_by']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['member__sha_number', 'member__first_name', 'member__last_name']
    readonly_fields = ['uploaded_at']
    
    actions = ['verify_documents']
    
    def verify_documents(self, request, queryset):
        updated = queryset.update(verified=True, verified_by=request.user)
        self.message_user(request, f'{updated} documents verified.')
    verify_documents.short_description = 'Verify selected documents'

# ============================================================================
# EMPLOYER ADMIN
# ============================================================================

class EmployerMemberInline(admin.TabularInline):
    model = EmployerMember
    extra = 0
    readonly_fields = ['calculate_monthly_contribution']
    
    def calculate_monthly_contribution(self, obj):
        if obj.pk:
            return f"KSh {obj.calculate_monthly_contribution():,.2f}"
        return "Save to calculate"

@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'registration_number', 'contact_person_name',
        'employee_count', 'status', 'registration_date'
    ]
    list_filter = ['status', 'industry', 'county', 'registration_date']
    search_fields = ['company_name', 'registration_number', 'tax_pin', 'email']
    readonly_fields = ['registration_date']
    inlines = [EmployerMemberInline]
    
    fieldsets = (
        ('Company Information', {
            'fields': (
                'company_name', 'registration_number', 'tax_pin', 'industry'
            )
        }),
        ('Contact Information', {
            'fields': (
                ('email', 'phone_number'),
                'postal_address', 'physical_address', 'county'
            )
        }),
        ('Contact Person', {
            'fields': (
                'contact_person_name', 'contact_person_phone', 'contact_person_email'
            )
        }),
        ('Status', {
            'fields': ('status', 'registration_date', 'approved_by')
        })
    )
    
    def employee_count(self, obj):
        return obj.employees.filter(is_active=True).count()
    employee_count.short_description = 'Active Employees'

@admin.register(EmployerMember)
class EmployerMemberAdmin(admin.ModelAdmin):
    list_display = [
        'employer', 'member_name', 'employee_number', 'monthly_salary',
        'monthly_contribution', 'is_active'
    ]
    list_filter = ['is_active', 'employer', 'date_joined']
    search_fields = [
        'employer__company_name', 'member__sha_number',
        'member__first_name', 'member__last_name', 'employee_number'
    ]
    
    def member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}"
    member_name.short_description = 'Member Name'
    
    def monthly_contribution(self, obj):
        return f"KSh {obj.calculate_monthly_contribution():,.2f}"
    monthly_contribution.short_description = 'Monthly Contribution'

# ============================================================================
# HOSPITAL ADMIN
# ============================================================================

class HospitalStaffInline(admin.TabularInline):
    model = HospitalStaff
    extra = 0
    readonly_fields = ['date_joined']

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'hospital_type', 'level', 'county', 'status',
        'active_staff_count', 'registration_date'
    ]
    list_filter = ['hospital_type', 'level', 'status', 'county', 'registration_date']
    search_fields = ['name', 'registration_number', 'email', 'phone_number']
    readonly_fields = ['registration_date']
    inlines = [HospitalStaffInline]
    
    fieldsets = (
        ('Hospital Information', {
            'fields': ('name', 'registration_number', 'hospital_type', 'level')
        }),
        ('Contact Information', {
            'fields': (
                ('email', 'phone_number'),
                'postal_address', 'physical_address',
                ('county', 'subcounty')
            )
        }),
        ('License Information', {
            'fields': ('license_number', 'license_expiry_date')
        }),
        ('Status', {
            'fields': ('status', 'registration_date', 'approved_by')
        })
    )
    
    def active_staff_count(self, obj):
        return obj.staff.filter(is_active=True).count()
    active_staff_count.short_description = 'Active Staff'

@admin.register(HospitalStaff)
class HospitalStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'hospital', 'role', 'staff_number', 'is_active']
    list_filter = ['role', 'is_active', 'hospital', 'date_joined']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'hospital__name', 'staff_number'
    ]

# ============================================================================
# CONTRIBUTION ADMIN
# ============================================================================

@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = [
        'member', 'contribution_month', 'amount', 'payment_method',
        'status', 'payment_date', 'employer'
    ]
    list_filter = [
        'contribution_type', 'payment_method', 'status', 
        'payment_date', 'contribution_month'
    ]
    search_fields = [
        'member__sha_number', 'member__first_name', 'member__last_name',
        'payment_reference', 'mpesa_transaction_id'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('member', 'employer', 'contribution_type')
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'contribution_month', 'payment_date',
                'payment_method', 'payment_reference', 'status'
            )
        }),
        ('M-Pesa Details', {
            'fields': ('mpesa_transaction_id', 'mpesa_phone_number'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'created_at')
        })
    )

# ============================================================================
# OTP AND SECURITY ADMIN
# ============================================================================

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = [
        'member', 'purpose', 'otp_code', 'hospital', 
        'is_used', 'created_at', 'expires_at'
    ]
    list_filter = ['purpose', 'is_used', 'created_at', 'hospital']
    search_fields = [
        'member__sha_number', 'otp_code', 'phone_number', 'email'
    ]
    readonly_fields = ['created_at', 'used_at', 'otp_code']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['otp_code']
        return self.readonly_fields

# ============================================================================
# HOSPITAL VISIT ADMIN
# ============================================================================

@admin.register(HospitalVisit)
class HospitalVisitAdmin(admin.ModelAdmin):
    list_display = [
        'visit_number', 'member', 'hospital', 'visit_type',
        'status', 'visit_date', 'otp_verified'
    ]
    list_filter = [
        'visit_type', 'status', 'otp_verified', 
        'visit_date', 'hospital'
    ]
    search_fields = [
        'visit_number', 'member__sha_number', 'member__first_name',
        'member__last_name', 'hospital__name'
    ]
    readonly_fields = ['visit_number', 'created_at', 'otp_verified_at']
    date_hierarchy = 'visit_date'
    
    fieldsets = (
        ('Visit Information', {
            'fields': (
                'visit_number', 'member', 'hospital', 'visit_type',
                'visit_date', 'status'
            )
        }),
        ('Check-in/out', {
            'fields': ('check_in_time', 'check_out_time', 'attending_staff')
        }),
        ('OTP Verification', {
            'fields': ('otp_verified', 'otp_verified_at', 'otp')
        }),
        ('Medical Information', {
            'fields': (
                'chief_complaint', 'consultation_notes',
                'diagnosis', 'treatment_plan'
            )
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    )

# ============================================================================
# MEDICINE AND PHARMACY ADMIN
# ============================================================================

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'generic_name', 'category', 'dosage_form',
        'unit_cost', 'requires_prescription', 'is_active'
    ]
    list_filter = ['category', 'requires_prescription', 'is_active', 'manufacturer']
    search_fields = ['name', 'generic_name', 'brand_name', 'manufacturer']
    readonly_fields = ['created_at']

@admin.register(PharmacyStock)
class PharmacyStockAdmin(admin.ModelAdmin):
    list_display = [
        'hospital', 'medicine_name', 'current_stock', 'minimum_stock_level',
        'stock_status', 'expiry_date', 'expired_status'
    ]
    list_filter = [
        'hospital', 'medicine__category', 'expiry_date',
        'last_restocked_date'
    ]
    search_fields = [
        'hospital__name', 'medicine__name', 'medicine__generic_name',
        'batch_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def medicine_name(self, obj):
        return obj.medicine.name
    medicine_name.short_description = 'Medicine'
    
    def stock_status(self, obj):
        if obj.is_low_stock():
            return format_html('<span style="color: red;">Low Stock</span>')
        return format_html('<span style="color: green;">Normal</span>')
    stock_status.short_description = 'Stock Status'
    
    def expired_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Valid</span>')
    expired_status.short_description = 'Expiry Status'

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0
    readonly_fields = ['is_fully_dispensed']

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_number', 'member_name', 'prescribed_by',
        'status', 'prescribed_date', 'collection_otp_verified'
    ]
    list_filter = [
        'status', 'prescribed_date', 'dispensed_date',
        'collection_otp_verified', 'visit__hospital'
    ]
    search_fields = [
        'prescription_number', 'visit__member__sha_number',
        'visit__member__first_name', 'visit__member__last_name'
    ]
    readonly_fields = ['prescription_number', 'prescribed_date', 'dispensed_date']
    inlines = [PrescriptionItemInline]
    
    def member_name(self, obj):
        return f"{obj.visit.member.first_name} {obj.visit.member.last_name}"
    member_name.short_description = 'Member'

# ============================================================================
# CLAIMS ADMIN
# ============================================================================

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = [
        'claim_number', 'hospital', 'member_name', 'claim_type',
        'amount_claimed', 'amount_approved', 'status', 'submitted_date'
    ]
    list_filter = [
        'claim_type', 'status', 'submitted_date', 'reviewed_date', 'hospital'
    ]
    search_fields = [
        'claim_number', 'hospital__name', 'visit__member__sha_number',
        'visit__member__first_name', 'visit__member__last_name'
    ]
    readonly_fields = ['claim_number', 'submitted_date', 'reviewed_date']
    date_hierarchy = 'submitted_date'
    
    actions = ['approve_claims', 'reject_claims']
    
    fieldsets = (
        ('Claim Information', {
            'fields': (
                'claim_number', 'hospital', 'visit', 'claim_type'
            )
        }),
        ('Financial Details', {
            'fields': ('amount_claimed', 'amount_approved')
        }),
        ('Status and Review', {
            'fields': (
                'status', 'submitted_date', 'reviewed_date', 'reviewed_by'
            )
        }),
        ('Supporting Information', {
            'fields': ('supporting_documents', 'review_notes', 'rejection_reason')
        })
    )
    
    def member_name(self, obj):
        member = obj.visit.member
        return f"{member.first_name} {member.last_name}"
    member_name.short_description = 'Member'
    
    def approve_claims(self, request, queryset):
        updated = queryset.filter(status='submitted').update(
            status='approved',
            reviewed_date=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} claims approved.')
    approve_claims.short_description = 'Approve selected claims'
    
    def reject_claims(self, request, queryset):
        updated = queryset.filter(status='submitted').update(
            status='rejected',
            reviewed_date=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} claims rejected.')
    reject_claims.short_description = 'Reject selected claims'

# ============================================================================
# NOTIFICATION ADMIN
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_user', 'notification_type', 'method', 'title',
        'is_sent', 'sent_at', 'read_at'
    ]
    list_filter = [
        'notification_type', 'method', 'is_sent', 'sent_at'
    ]
    search_fields = [
        'recipient_user__username', 'title', 'message',
        'phone_number', 'email_address'
    ]
    readonly_fields = ['sent_at', 'read_at']

# ============================================================================
# AUDIT LOG ADMIN
# ============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'action_type', 'model_name', 'object_id',
        'timestamp', 'ip_address'
    ]
    list_filter = [
        'action_type', 'model_name', 'timestamp'
    ]
    search_fields = [
        'user__username', 'model_name', 'object_id',
        'description', 'ip_address'
    ]
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Audit logs should not be manually created
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should not be deleted

# ============================================================================
# GOVERNMENT REPORT ADMIN
# ============================================================================

@admin.register(GovernmentReport)
class GovernmentReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_type', 'report_period', 'generated_by',
        'generated_at', 'has_file'
    ]
    list_filter = [
        'report_type', 'generated_at', 'report_period_start'
    ]
    search_fields = [
        'report_type', 'generated_by__username'
    ]
    readonly_fields = ['generated_at', 'report_data_display']
    
    fieldsets = (
        ('Report Information', {
            'fields': (
                'report_type', 'report_period_start', 'report_period_end'
            )
        }),
        ('Generation Details', {
            'fields': ('generated_by', 'generated_at')
        }),
        ('Report Data', {
            'fields': ('report_data_display', 'report_file'),
            'classes': ('collapse',)
        })
    )
    
    def report_period(self, obj):
        return f"{obj.report_period_start} to {obj.report_period_end}"
    report_period.short_description = 'Period'
    
    def has_file(self, obj):
        if obj.report_file:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_file.short_description = 'File'
    
    def report_data_display(self, obj):
        if obj.report_data:
            return format_html(
                '<pre style="max-height: 300px; overflow: auto;">{}</pre>',
                json.dumps(obj.report_data, indent=2)
            )
        return "No data"
    report_data_display.short_description = 'Report Data'

# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

admin.site.site_header = "SHA Digital Platform Administration"
admin.site.site_title = "SHA Admin"
admin.site.index_title = "Welcome to SHA Digital Platform"

# Custom admin views for dashboard statistics
class AdminDashboard:
    """Custom dashboard with key statistics"""
    
    @staticmethod
    def get_member_stats():
        from django.db.models import Count
        return {
            'total_members': SHAMember.objects.count(),
            'active_members': SHAMember.objects.filter(status='active').count(),
            'pending_approvals': SHAMember.objects.filter(status='pending').count(),
        }
    
    @staticmethod
    def get_contribution_stats():
        current_month = timezone.now().date().replace(day=1)
        return {
            'monthly_contributions': Contribution.objects.filter(
                contribution_month=current_month,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'pending_contributions': Contribution.objects.filter(
                status='pending'
            ).count(),
        }
    
    @staticmethod
    def get_claim_stats():
        return {
            'pending_claims': Claim.objects.filter(status='submitted').count(),
            'approved_claims_value': Claim.objects.filter(
                status='approved'
            ).aggregate(total=Sum('amount_approved'))['total'] or 0,
        }
