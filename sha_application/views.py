# admin_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models.functions import TruncMonth, TruncDate
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    User, SHAMember, Employer, Hospital, HospitalStaff, Contribution,
    HospitalVisit, Prescription, Claim, Notification, AuditLog,
    County, SubCounty, Medicine, PharmacyStock
)

# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def admin_login(request):
    """Admin login view"""
    if request.user.is_authenticated and request.user.user_type == 'admin':
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.user_type == 'admin':
            login(request, user)
            # Log the login
            AuditLog.objects.create(
                user=user,
                action_type='login',
                model_name='User',
                object_id=str(user.id),
                description=f'Admin {user.username} logged in',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            messages.success(request, 'Welcome to SHA Admin Dashboard!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    
    return render(request, 'admin/login.html')

@login_required
def admin_logout(request):
    """Admin logout view"""
    if request.user.user_type == 'admin':
        # Log the logout
        AuditLog.objects.create(
            user=request.user,
            action_type='logout',
            model_name='User',
            object_id=str(request.user.id),
            description=f'Admin {request.user.username} logged out',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')

# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('admin_login')
    
    # Get current date ranges
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    this_year = today.year
    
    # Basic statistics
    total_members = SHAMember.objects.count()
    active_members = SHAMember.objects.filter(status='active').count()
    pending_members = SHAMember.objects.filter(status='pending').count()
    
    total_hospitals = Hospital.objects.count()
    active_hospitals = Hospital.objects.filter(status='active').count()
    pending_hospitals = Hospital.objects.filter(status='pending').count()
    
    total_employers = Employer.objects.count()
    active_employers = Employer.objects.filter(status='active').count()
    
    # Financial statistics
    total_contributions = Contribution.objects.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    this_month_contributions = Contribution.objects.filter(
        status='completed',
        payment_date__gte=this_month_start
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Claims statistics
    total_claims = Claim.objects.count()
    pending_claims = Claim.objects.filter(status='submitted').count()
    approved_claims = Claim.objects.filter(status='approved').count()
    
    total_claims_amount = Claim.objects.aggregate(
        total=Sum('amount_claimed')
    )['total'] or Decimal('0.00')
    
    # Hospital visits
    total_visits = HospitalVisit.objects.count()
    this_month_visits = HospitalVisit.objects.filter(
        visit_date__gte=this_month_start
    ).count()
    
    # Recent activities
    recent_members = SHAMember.objects.select_related('county').order_by('-registration_date')[:10]
    recent_claims = Claim.objects.select_related('hospital', 'visit__member').order_by('-submitted_date')[:10]
    pending_approvals = SHAMember.objects.filter(status='pending').count() + \
                       Hospital.objects.filter(status='pending').count() + \
                       Employer.objects.filter(status='pending').count()
    
    # Monthly contribution trends (last 6 months)
    six_months_ago = this_month_start - timedelta(days=180)
    monthly_contributions = Contribution.objects.filter(
        status='completed',
        payment_date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')
    
    # Daily visits trend (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    daily_visits = HospitalVisit.objects.filter(
        visit_date__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('visit_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Top hospitals by visits
    top_hospitals = Hospital.objects.annotate(
        visit_count=Count('patient_visits')
    ).order_by('-visit_count')[:5]
    
    # System alerts
    low_stock_medicines = PharmacyStock.objects.filter(
        current_stock__lte=models.F('minimum_stock_level')
    ).select_related('hospital', 'medicine').count()
    
    expired_medicines = PharmacyStock.objects.filter(
        expiry_date__lt=today
    ).count()
    
    context = {
        'total_members': total_members,
        'active_members': active_members,
        'pending_members': pending_members,
        'total_hospitals': total_hospitals,
        'active_hospitals': active_hospitals,
        'pending_hospitals': pending_hospitals,
        'total_employers': total_employers,
        'active_employers': active_employers,
        'total_contributions': total_contributions,
        'this_month_contributions': this_month_contributions,
        'total_claims': total_claims,
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'total_claims_amount': total_claims_amount,
        'total_visits': total_visits,
        'this_month_visits': this_month_visits,
        'recent_members': recent_members,
        'recent_claims': recent_claims,
        'pending_approvals': pending_approvals,
        'monthly_contributions': list(monthly_contributions),
        'daily_visits': list(daily_visits),
        'top_hospitals': top_hospitals,
        'low_stock_medicines': low_stock_medicines,
        'expired_medicines': expired_medicines,
    }
    
    return render(request, 'admin/dashboard.html', context)

# ============================================================================
# MEMBER MANAGEMENT VIEWS
# ============================================================================

@login_required
def members_list(request):
    """List all SHA members with filtering and pagination"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    members = SHAMember.objects.select_related('county', 'subcounty').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    county_filter = request.GET.get('county')
    search_query = request.GET.get('search')
    
    if status_filter:
        members = members.filter(status=status_filter)
    
    if county_filter:
        members = members.filter(county_id=county_filter)
    
    if search_query:
        members = members.filter(
            Q(sha_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(members, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    counties = County.objects.all()
    status_choices = SHAMember.MEMBER_STATUS
    
    context = {
        'page_obj': page_obj,
        'counties': counties,
        'status_choices': status_choices,
        'current_status': status_filter,
        'current_county': county_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin/members/list.html', context)

@login_required
def member_detail(request, member_id):
    """View detailed information about a specific member"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    member = get_object_or_404(SHAMember, id=member_id)
    
    # Get related data
    contributions = member.contributions.order_by('-payment_date')[:10]
    hospital_visits = member.hospital_visits.select_related('hospital').order_by('-visit_date')[:10]
    employers = member.employers.select_related('employer').filter(is_active=True)
    documents = member.documents.order_by('-uploaded_at')
    
    # Statistics
    total_contributions = member.contributions.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_visits = member.hospital_visits.count()
    
    context = {
        'member': member,
        'contributions': contributions,
        'hospital_visits': hospital_visits,
        'employers': employers,
        'documents': documents,
        'total_contributions': total_contributions,
        'total_visits': total_visits,
    }
    
    return render(request, 'admin/members/detail.html', context)

@login_required
def approve_member(request, member_id):
    """Approve a pending member"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    member = get_object_or_404(SHAMember, id=member_id)
    
    if request.method == 'POST':
        if member.status == 'pending':
            member.status = 'active'
            member.approval_date = timezone.now()
            member.approved_by = request.user
            member.save()
            
            # Log the approval
            AuditLog.objects.create(
                user=request.user,
                action_type='approval',
                model_name='SHAMember',
                object_id=str(member.id),
                description=f'Member {member.sha_number} approved by {request.user.username}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Send notification to member
            Notification.objects.create(
                recipient_user=member.user,
                notification_type='registration_approved',
                method='sms',
                title='SHA Registration Approved',
                message=f'Your SHA registration has been approved. Your SHA number is {member.sha_number}.',
                phone_number=member.phone_number
            )
            
            messages.success(request, f'Member {member.sha_number} has been approved successfully.')
        else:
            messages.warning(request, 'Member is not in pending status.')
    
    return redirect('member_detail', member_id=member_id)

# ============================================================================
# HOSPITAL MANAGEMENT VIEWS
# ============================================================================

@login_required
def hospitals_list(request):
    """List all hospitals with filtering"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    hospitals = Hospital.objects.select_related('county', 'subcounty').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    county_filter = request.GET.get('county')
    search_query = request.GET.get('search')
    
    if status_filter:
        hospitals = hospitals.filter(status=status_filter)
    
    if type_filter:
        hospitals = hospitals.filter(hospital_type=type_filter)
    
    if county_filter:
        hospitals = hospitals.filter(county_id=county_filter)
    
    if search_query:
        hospitals = hospitals.filter(
            Q(name__icontains=search_query) |
            Q(registration_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(hospitals, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    counties = County.objects.all()
    status_choices = Hospital.HOSPITAL_STATUS
    type_choices = Hospital.HOSPITAL_TYPES
    
    context = {
        'page_obj': page_obj,
        'counties': counties,
        'status_choices': status_choices,
        'type_choices': type_choices,
        'current_status': status_filter,
        'current_type': type_filter,
        'current_county': county_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin/hospitals/list.html', context)

@login_required
def hospital_detail(request, hospital_id):
    """View detailed information about a specific hospital"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    hospital = get_object_or_404(Hospital, id=hospital_id)
    
    # Get related data
    staff = hospital.staff.select_related('user')[:10]
    recent_visits = hospital.patient_visits.select_related('member').order_by('-visit_date')[:10]
    claims = hospital.claims.order_by('-submitted_date')[:10]
    pharmacy_stock = hospital.pharmacy_stock.select_related('medicine').order_by('-updated_at')[:10]
    
    # Statistics
    total_visits = hospital.patient_visits.count()
    total_staff = hospital.staff.filter(is_active=True).count()
    total_claims = hospital.claims.count()
    total_claims_amount = hospital.claims.aggregate(
        total=Sum('amount_claimed')
    )['total'] or Decimal('0.00')
    
    context = {
        'hospital': hospital,
        'staff': staff,
        'recent_visits': recent_visits,
        'claims': claims,
        'pharmacy_stock': pharmacy_stock,
        'total_visits': total_visits,
        'total_staff': total_staff,
        'total_claims': total_claims,
        'total_claims_amount': total_claims_amount,
    }
    
    return render(request, 'admin/hospitals/detail.html', context)

# ============================================================================
# CLAIMS MANAGEMENT VIEWS
# ============================================================================

@login_required
def claims_list(request):
    """List all claims with filtering"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    claims = Claim.objects.select_related('hospital', 'visit__member').all()
    
    # Filtering
    status_filter = request.GET.get('status')
    hospital_filter = request.GET.get('hospital')
    claim_type_filter = request.GET.get('claim_type')
    
    if status_filter:
        claims = claims.filter(status=status_filter)
    
    if hospital_filter:
        claims = claims.filter(hospital_id=hospital_filter)
    
    if claim_type_filter:
        claims = claims.filter(claim_type=claim_type_filter)
    
    # Pagination
    paginator = Paginator(claims.order_by('-submitted_date'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    hospitals = Hospital.objects.filter(status='active')
    status_choices = Claim.CLAIM_STATUS
    type_choices = Claim.CLAIM_TYPES
    
    context = {
        'page_obj': page_obj,
        'hospitals': hospitals,
        'status_choices': status_choices,
        'type_choices': type_choices,
        'current_status': status_filter,
        'current_hospital': hospital_filter,
        'current_claim_type': claim_type_filter,
    }
    
    return render(request, 'admin/claims/list.html', context)

@login_required
def claim_detail(request, claim_id):
    """View and process a specific claim"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    claim = get_object_or_404(Claim, id=claim_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            approved_amount = request.POST.get('approved_amount')
            review_notes = request.POST.get('review_notes', '')
            
            try:
                approved_amount = Decimal(approved_amount)
                claim.status = 'approved'
                claim.amount_approved = approved_amount
                claim.review_notes = review_notes
                claim.reviewed_date = timezone.now()
                claim.reviewed_by = request.user
                claim.save()
                
                # Log the approval
                AuditLog.objects.create(
                    user=request.user,
                    action_type='approval',
                    model_name='Claim',
                    object_id=str(claim.id),
                    description=f'Claim {claim.claim_number} approved for KSh {approved_amount}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Claim approved for KSh {approved_amount}')
                
            except (ValueError, TypeError):
                messages.error(request, 'Invalid approved amount.')
        
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', '')
            
            if rejection_reason:
                claim.status = 'rejected'
                claim.rejection_reason = rejection_reason
                claim.reviewed_date = timezone.now()
                claim.reviewed_by = request.user
                claim.save()
                
                # Log the rejection
                AuditLog.objects.create(
                    user=request.user,
                    action_type='rejection',
                    model_name='Claim',
                    object_id=str(claim.id),
                    description=f'Claim {claim.claim_number} rejected: {rejection_reason}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 'Claim rejected successfully.')
            else:
                messages.error(request, 'Rejection reason is required.')
    
    context = {
        'claim': claim,
    }
    
    return render(request, 'admin/claims/detail.html', context)

# ============================================================================
# REPORTS AND ANALYTICS VIEWS
# ============================================================================

@login_required
def reports_dashboard(request):
    """Reports and analytics dashboard"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    return render(request, 'admin/reports/dashboard.html')

@login_required
def financial_reports(request):
    """Financial reports and analytics"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = timezone.now().date().replace(month=1, day=1)  # Start of year
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Contributions analysis
    contributions_data = Contribution.objects.filter(
        status='completed',
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date
    )
    
    total_contributions = contributions_data.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    contribution_count = contributions_data.count()
    avg_contribution = total_contributions / contribution_count if contribution_count > 0 else Decimal('0.00')
    
    # Contributions by type
    contributions_by_type = contributions_data.values('contribution_type').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Claims analysis
    claims_data = Claim.objects.filter(
        submitted_date__date__gte=start_date,
        submitted_date__date__lte=end_date
    )
    
    total_claims_amount = claims_data.aggregate(total=Sum('amount_claimed'))['total'] or Decimal('0.00')
    approved_claims_amount = claims_data.filter(status='approved').aggregate(
        total=Sum('amount_approved')
    )['total'] or Decimal('0.00')
    
    # Claims by status
    claims_by_status = claims_data.values('status').annotate(
        total=Sum('amount_claimed'),
        count=Count('id')
    )
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_contributions': total_contributions,
        'contribution_count': contribution_count,
        'avg_contribution': avg_contribution,
        'contributions_by_type': contributions_by_type,
        'total_claims_amount': total_claims_amount,
        'approved_claims_amount': approved_claims_amount,
        'claims_by_status': claims_by_status,
    }
    
    return render(request, 'admin/reports/financial.html', context)

# ============================================================================
# SYSTEM MANAGEMENT VIEWS
# ============================================================================

@login_required
def system_settings(request):
    """System settings and configuration"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    return render(request, 'admin/system/settings.html')

@login_required
def audit_logs(request):
    """View system audit logs"""
    if request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('admin_login')
    
    logs = AuditLog.objects.select_related('user').all()
    
    # Filtering
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    model_filter = request.GET.get('model')
    
    if action_filter:
        logs = logs.filter(action_type=action_filter)
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if model_filter:
        logs = logs.filter(model_name=model_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    action_choices = AuditLog.ACTION_TYPES
    users = User.objects.filter(user_type='admin')
    models = AuditLog.objects.values_list('model_name', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'action_choices': action_choices,
        'users': users,
        'models': models,
        'current_action': action_filter,
        'current_user': user_filter,
        'current_model': model_filter,
    }
    
    return render(request, 'admin/system/audit_logs.html', context)

# ============================================================================
# API VIEWS FOR AJAX REQUESTS
# ============================================================================

@login_required
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics (for real-time updates)"""
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    today = timezone.now().date()
    
    stats = {
        'total_members': SHAMember.objects.count(),
        'pending_members': SHAMember.objects.filter(status='pending').count(),
        'total_hospitals': Hospital.objects.count(),
        'pending_claims': Claim.objects.filter(status='submitted').count(),
        'today_visits': HospitalVisit.objects.filter(visit_date__date=today).count(),
        'low_stock_alerts': PharmacyStock.objects.filter(
            current_stock__lte=models.F('minimum_stock_level')
        ).count(),
    }
    
    return JsonResponse(stats)

from django.db import models  # Add this import at the top