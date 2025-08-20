from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from django.utils import timezone
import uuid
import secrets
import string
from decimal import Decimal

# ============================================================================
# CUSTOM USER MODEL
# ============================================================================

class User(AbstractUser):
    USER_TYPES = [
        ('member', 'SHA Member'),
        ('hospital', 'Hospital Staff'),
        ('employer', 'Employer'),
        ('admin', 'SHA Administrator'),
    ]
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

# ============================================================================
# CORE MODELS
# ============================================================================

class County(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name

class SubCounty(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='subcounties')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    
    class Meta:
        unique_together = ['county', 'name']
    
    def __str__(self):
        return f"{self.name}, {self.county.name}"

# ============================================================================
# MEMBER MODELS
# ============================================================================

class SHAMember(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    MEMBER_STATUS = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sha_member')
    sha_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, unique=True, validators=[
        RegexValidator(regex=r'^\d{8}$', message='ID number must be 8 digits')
    ])
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Contact Information
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    postal_address = models.CharField(max_length=200, blank=True)
    physical_address = models.TextField()
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE)
    
    # Biometric Data
    fingerprint_template = models.BinaryField(null=True, blank=True)
    photo = models.ImageField(upload_to='member_photos/', null=True, blank=True)
    
    # Status and Metadata
    status = models.CharField(max_length=20, choices=MEMBER_STATUS, default='pending')
    registration_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_members')
    
    # QR Code for ID card
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.sha_number:
            self.sha_number = self.generate_sha_number()
        super().save(*args, **kwargs)
    
    def generate_sha_number(self):
        # Generate SHA number: SHA + County Code + Random 6 digits
        random_digits = ''.join(secrets.choice(string.digits) for _ in range(6))
        return f"SHA{self.county.code}{random_digits}"
    
    def __str__(self):
        return f"{self.sha_number} - {self.first_name} {self.last_name}"

class MemberDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id_copy', 'ID Copy'),
        ('birth_certificate', 'Birth Certificate'),
        ('passport_photo', 'Passport Photo'),
        ('payslip', 'Payslip'),
        ('marriage_certificate', 'Marriage Certificate'),
        ('other', 'Other'),
    ]
    
    member = models.ForeignKey(SHAMember, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='member_documents/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.member.sha_number} - {self.get_document_type_display()}"

# ============================================================================
# EMPLOYER MODELS
# ============================================================================

class Employer(models.Model):
    EMPLOYER_STATUS = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employer_profile'  # 👈 clearer than just 'employer'
    )
    company_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    tax_pin = models.CharField(max_length=20, unique=True)
    industry = models.CharField(max_length=100)
    
    # Contact Information
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    postal_address = models.CharField(max_length=200)
    physical_address = models.TextField()
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    
    # Contact Person
    contact_person_name = models.CharField(max_length=200)
    contact_person_phone = models.CharField(max_length=15)
    contact_person_email = models.EmailField()
    
    status = models.CharField(
        max_length=20,
        choices=EMPLOYER_STATUS,
        default='pending'
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employers_approved'  # 👈 avoids clash
    )
    
    def __str__(self):
        return self.company_name


class EmployerMember(models.Model):
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name='employees')
    member = models.ForeignKey(SHAMember, on_delete=models.CASCADE, related_name='employers')
    employee_number = models.CharField(max_length=50)
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    contribution_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('2.75'))  # 2.75%
    date_joined = models.DateField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['employer', 'member']
    
    def calculate_monthly_contribution(self):
        return (self.monthly_salary * self.contribution_rate) / 100
    
    def __str__(self):
        return f"{self.employer.company_name} - {self.member.sha_number}"

# ============================================================================
# HOSPITAL MODELS
# ============================================================================

class Hospital(models.Model):
    HOSPITAL_TYPES = [
        ('public', 'Public Hospital'),
        ('private', 'Private Hospital'),
        ('faith_based', 'Faith-Based Hospital'),
        ('ngo', 'NGO Hospital'),
    ]
    
    HOSPITAL_STATUS = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    hospital_type = models.CharField(max_length=20, choices=HOSPITAL_TYPES)
    level = models.IntegerField(choices=[(i, f'Level {i}') for i in range(1, 7)])  # Level 1-6
    
    # Contact Information
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    postal_address = models.CharField(max_length=200)
    physical_address = models.TextField()
    county = models.ForeignKey(County, on_delete=models.CASCADE)
    subcounty = models.ForeignKey(SubCounty, on_delete=models.CASCADE)
    
    # License Information
    license_number = models.CharField(max_length=100)
    license_expiry_date = models.DateField()
    
    status = models.CharField(max_length=20, choices=HOSPITAL_STATUS, default='pending')
    registration_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name

class HospitalStaff(models.Model):
    STAFF_ROLES = [
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('pharmacist', 'Pharmacist'),
        ('clerk', 'Clerk'),
        ('administrator', 'Administrator'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='hospital_staff')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='staff')
    staff_number = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=STAFF_ROLES)
    license_number = models.CharField(max_length=100, blank=True)  # For doctors, nurses, etc.
    is_active = models.BooleanField(default=True)
    date_joined = models.DateField()
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.hospital.name}"

# ============================================================================
# CONTRIBUTION MODELS
# ============================================================================

class Contribution(models.Model):
    CONTRIBUTION_TYPES = [
        ('individual', 'Individual'),
        ('employer', 'Employer'),
        ('government', 'Government Subsidy'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('payroll', 'Payroll Deduction'),
    ]
    
    member = models.ForeignKey(SHAMember, on_delete=models.CASCADE, related_name='contributions')
    employer = models.ForeignKey(Employer, on_delete=models.SET_NULL, null=True, blank=True, related_name='contributions')
    
    contribution_type = models.CharField(max_length=20, choices=CONTRIBUTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    contribution_month = models.DateField()  # Month and year being paid for
    payment_date = models.DateTimeField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_reference = models.CharField(max_length=100)  # M-Pesa code, bank reference, etc.
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # M-Pesa specific fields
    mpesa_transaction_id = models.CharField(max_length=100, blank=True)
    mpesa_phone_number = models.CharField(max_length=15, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['member', 'contribution_month']  # One contribution per member per month
    
    def __str__(self):
        return f"{self.member.sha_number} - {self.contribution_month.strftime('%B %Y')} - KSh {self.amount}"

# ============================================================================
# OTP AND SECURITY MODELS
# ============================================================================

class OTP(models.Model):
    OTP_PURPOSES = [
        ('hospital_visit', 'Hospital Visit Verification'),
        ('medicine_collection', 'Medicine Collection'),
        ('account_verification', 'Account Verification'),
        ('password_reset', 'Password Reset'),
    ]
    
    member = models.ForeignKey(SHAMember, on_delete=models.CASCADE, related_name='otps')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True)
    purpose = models.CharField(max_length=30, choices=OTP_PURPOSES)
    otp_code = models.CharField(max_length=6)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)  # 10 minutes expiry
        super().save(*args, **kwargs)
    
    def generate_otp(self):
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.member.sha_number} - {self.purpose} - {self.otp_code}"

# ============================================================================
# HOSPITAL VISIT AND TREATMENT MODELS
# ============================================================================

class HospitalVisit(models.Model):
    VISIT_STATUS = [
        ('scheduled', 'Scheduled'),
        ('checked_in', 'Checked In'),
        ('in_consultation', 'In Consultation'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    VISIT_TYPES = [
        ('consultation', 'Consultation'),
        ('emergency', 'Emergency'),
        ('referral', 'Referral'),
        ('follow_up', 'Follow-up'),
        ('admission', 'Admission'),
    ]
    
    member = models.ForeignKey(SHAMember, on_delete=models.CASCADE, related_name='hospital_visits')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='patient_visits')
    visit_number = models.CharField(max_length=50, unique=True)
    
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPES)
    visit_date = models.DateTimeField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=VISIT_STATUS, default='scheduled')
    
    # OTP Verification
    otp_verified = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    otp = models.ForeignKey(OTP, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Staff handling
    attending_staff = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Chief complaint and notes
    chief_complaint = models.TextField()
    consultation_notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.visit_number:
            self.visit_number = self.generate_visit_number()
        super().save(*args, **kwargs)
    
    def generate_visit_number(self):
        today = timezone.now().strftime('%Y%m%d')
        random_digits = ''.join(secrets.choice(string.digits) for _ in range(4))
        return f"VIS{today}{random_digits}"
    
    def __str__(self):
        return f"{self.visit_number} - {self.member.sha_number} at {self.hospital.name}"

# ============================================================================
# PHARMACY AND MEDICINE MODELS
# ============================================================================

class Medicine(models.Model):
    MEDICINE_CATEGORIES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream/Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=MEDICINE_CATEGORIES)
    dosage_form = models.CharField(max_length=100)  # e.g., "500mg tablet", "10ml vial"
    manufacturer = models.CharField(max_length=200)
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    description = models.TextField(blank=True)
    requires_prescription = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.dosage_form}"

class PharmacyStock(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='pharmacy_stock')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    
    current_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    minimum_stock_level = models.IntegerField(default=10)
    maximum_stock_level = models.IntegerField(default=1000)
    
    last_restocked_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['hospital', 'medicine', 'batch_number']
    
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock_level
    
    def is_expired(self):
        return timezone.now().date() > self.expiry_date
    
    def __str__(self):
        return f"{self.hospital.name} - {self.medicine.name} - Stock: {self.current_stock}"

class Prescription(models.Model):
    PRESCRIPTION_STATUS = [
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
        ('partially_dispensed', 'Partially Dispensed'),
        ('cancelled', 'Cancelled'),
    ]
    
    visit = models.ForeignKey(HospitalVisit, on_delete=models.CASCADE, related_name='prescriptions')
    prescription_number = models.CharField(max_length=50, unique=True)
    prescribed_by = models.ForeignKey(HospitalStaff, on_delete=models.CASCADE, related_name='prescriptions')
    
    status = models.CharField(max_length=20, choices=PRESCRIPTION_STATUS, default='pending')
    prescribed_date = models.DateTimeField(auto_now_add=True)
    dispensed_date = models.DateTimeField(null=True, blank=True)
    dispensed_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_prescriptions')
    
    # OTP for medicine collection
    collection_otp_verified = models.BooleanField(default=False)
    collection_otp = models.ForeignKey(OTP, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescription_collections')
    
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.prescription_number:
            self.prescription_number = self.generate_prescription_number()
        super().save(*args, **kwargs)
    
    def generate_prescription_number(self):
        today = timezone.now().strftime('%Y%m%d')
        random_digits = ''.join(secrets.choice(string.digits) for _ in range(4))
        return f"RX{today}{random_digits}"
    
    def __str__(self):
        return f"{self.prescription_number} - {self.visit.member.sha_number}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    
    quantity_prescribed = models.IntegerField()
    quantity_dispensed = models.IntegerField(default=0)
    dosage_instructions = models.TextField()  # e.g., "Take 2 tablets twice daily after meals"
    duration_days = models.IntegerField()  # Number of days to take the medicine
    
    def is_fully_dispensed(self):
        return self.quantity_dispensed >= self.quantity_prescribed
    
    def __str__(self):
        return f"{self.prescription.prescription_number} - {self.medicine.name}"

# ============================================================================
# CLAIMS AND REIMBURSEMENT MODELS
# ============================================================================

class Claim(models.Model):
    CLAIM_TYPES = [
        ('consultation', 'Consultation'),
        ('treatment', 'Treatment'),
        ('medicine', 'Medicine'),
        ('procedure', 'Medical Procedure'),
        ('admission', 'Hospital Admission'),
        ('emergency', 'Emergency Care'),
    ]
    
    CLAIM_STATUS = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='claims')
    visit = models.ForeignKey(HospitalVisit, on_delete=models.CASCADE, related_name='claims')
    claim_number = models.CharField(max_length=50, unique=True)
    
    claim_type = models.CharField(max_length=20, choices=CLAIM_TYPES)
    amount_claimed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=CLAIM_STATUS, default='submitted')
    submitted_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Supporting documents
    supporting_documents = models.FileField(upload_to='claim_documents/', null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = self.generate_claim_number()
        super().save(*args, **kwargs)
    
    def generate_claim_number(self):
        today = timezone.now().strftime('%Y%m%d')
        random_digits = ''.join(secrets.choice(string.digits) for _ in range(4))
        return f"CLM{today}{random_digits}"
    
    def __str__(self):
        return f"{self.claim_number} - {self.hospital.name} - KSh {self.amount_claimed}"

# ============================================================================
# NOTIFICATION AND AUDIT MODELS
# ============================================================================

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('contribution_reminder', 'Contribution Reminder'),
        ('claim_update', 'Claim Update'),
        ('medicine_availability', 'Medicine Availability'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('registration_approved', 'Registration Approved'),
        ('otp_code', 'OTP Code'),
        ('system_alert', 'System Alert'),
    ]
    
    NOTIFICATION_METHODS = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('system', 'System Notification'),
    ]
    
    recipient_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    method = models.CharField(max_length=10, choices=NOTIFICATION_METHODS)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    
    # SMS/Email specific fields
    phone_number = models.CharField(max_length=15, blank=True)
    email_address = models.EmailField(blank=True)
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient_user.username}"

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('approval', 'Approval'),
        ('rejection', 'Rejection'),
        ('payment', 'Payment'),
        ('otp_generation', 'OTP Generation'),
        ('otp_verification', 'OTP Verification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)  # Model that was affected
    object_id = models.CharField(max_length=100)   # ID of the affected object
    
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.model_name} - {self.timestamp}"

# ============================================================================
# GOVERNMENT REPORTING MODELS
# ============================================================================

class GovernmentReport(models.Model):
    REPORT_TYPES = [
        ('monthly_summary', 'Monthly Summary'),
        ('quarterly_summary', 'Quarterly Summary'),
        ('annual_summary', 'Annual Summary'),
        ('financial_report', 'Financial Report'),
        ('membership_report', 'Membership Report'),
        ('hospital_utilization', 'Hospital Utilization'),
        ('fraud_detection', 'Fraud Detection Report'),
    ]
    
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    report_period_start = models.DateField()
    report_period_end = models.DateField()
    
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Report data (JSON field to store flexible report data)
    report_data = models.JSONField()
    
    # Generated report file
    report_file = models.FileField(upload_to='government_reports/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.report_period_start} to {self.report_period_end}"