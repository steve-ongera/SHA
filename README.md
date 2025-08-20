# SHA Digital Platform

A comprehensive Django web application that digitizes the operations of the Social Health Authority (SHA) system in Kenya, focusing on hospital workflows with different portals for members, hospitals, employers, and SHA administrators.

## 🏥 Overview

The SHA Digital Platform modernizes healthcare service delivery in Kenya by providing:
- **Digital membership management** with SHA number generation
- **Seamless hospital workflows** with OTP verification
- **Employer contribution management** with bulk uploads
- **Comprehensive claims processing** system
- **Pharmacy stock management** integration
- **Real-time reporting** and fraud detection

## 🚀 Features

### 👥 Member (Patient) Portal
- ✅ **Registration**: Personal details, ID, biometrics, document uploads
- 🆔 **SHA Number**: Unique membership ID generation
- 📊 **Dashboard**: Contribution history, benefit entitlements, treatment history
- 💰 **M-Pesa Integration**: Contributions and renewals
- 🔐 **OTP Verification**: SMS/email codes for hospital services
- 💊 **Prescription Tracking**: Medicine dispensed history
- 📱 **QR Code**: Digital ID card generation

### 🏥 Hospital Portal
- ✅ **Member Verification**: SHA number + OTP validation
- 📝 **Patient Management**: Admission and registration
- 🆓 **Free Services**: Consultation, treatment, medicine for SHA members
- 💊 **Pharmacy Integration**: Drug dispensing module
- 💰 **Claims Submission**: Reimbursement requests to SHA
- 📈 **Reports**: Usage statistics, claims status

### 🏢 Employer Portal
- 👥 **Employee Registration**: Bulk SHA enrollment
- 📁 **Bulk Upload**: CSV/Excel employee data import
- 💰 **Contribution Management**: Payroll deductions, obligations
- 🏦 **Payment Integration**: M-Pesa Paybill/Bank transfers
- 📊 **Reporting**: Contribution reports and downloads

### 🛠️ SHA Admin Portal
- ✅ **Approvals**: Member registrations, hospital registrations
- 💰 **Financial Oversight**: Contributions, claims, fund disbursement
- 🔍 **Fraud Detection**: Duplicate claims, unusual usage patterns
- 🏥 **Provider Management**: Approved hospitals and pharmacies
- 📈 **Government Reporting**: Monthly/annual reports

## 🔧 Technical Stack

- **Backend**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL (recommended) or MySQL
- **Authentication**: JWT for API security
- **File Storage**: Django's file handling with cloud storage support
- **Task Queue**: Celery for background tasks (SMS, email notifications)
- **Cache**: Redis for session management and caching
- **API**: RESTful APIs for mobile app integration

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+ or MySQL 8+
- Redis 6+
- Node.js 16+ (for frontend assets)
- Git

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/sha-digital-platform.git
cd sha-digital-platform
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory:
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/sha_db

# Security
SECRET_KEY=your-super-secret-key-here
DEBUG=True

# M-Pesa Configuration
MPESA_CONSUMER_KEY=your-mpesa-consumer-key
MPESA_CONSUMER_SECRET=your-mpesa-consumer-secret
MPESA_SHORTCODE=your-business-shortcode
MPESA_PASSKEY=your-mpesa-passkey

# SMS Configuration (Africa's Talking or Twilio)
SMS_API_KEY=your-sms-api-key
SMS_USERNAME=your-sms-username

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# File Storage (AWS S3 or local)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=sha-platform-files
AWS_S3_REGION_NAME=us-east-1

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 5. Database Setup
```bash
# Create database
createdb sha_db  # PostgreSQL
# or CREATE DATABASE sha_db; -- MySQL

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata fixtures/counties.json
python manage.py loaddata fixtures/medicines.json
```

### 6. Static Files and Media
```bash
python manage.py collectstatic
mkdir -p media/{member_photos,member_documents,qr_codes,claim_documents,government_reports}
```

### 7. Start Services

#### Start Redis (required for Celery)
```bash
redis-server
```

#### Start Celery Worker (new terminal)
```bash
celery -A sha_platform worker --loglevel=info
```

#### Start Celery Beat (scheduler - new terminal)
```bash
celery -A sha_platform beat --loglevel=info
```

#### Start Django Development Server
```bash
python manage.py runserver
```

## 📱 API Documentation

### Authentication
All API endpoints require JWT authentication (except registration endpoints).

```bash
# Get JWT token
POST /api/auth/login/
{
    "username": "your_username",
    "password": "your_password"
}

# Use token in headers
Authorization: Bearer your_jwt_token_here
```

### Key API Endpoints

#### Member APIs
```bash
# Member registration
POST /api/members/register/

# Get member profile
GET /api/members/profile/

# Generate OTP for hospital visit
POST /api/members/generate-otp/

# Verify OTP
POST /api/members/verify-otp/

# Get contribution history
GET /api/members/contributions/

# Get treatment history
GET /api/members/treatments/
```

#### Hospital APIs
```bash
# Verify member
POST /api/hospitals/verify-member/

# Register patient visit
POST /api/hospitals/register-visit/

# Get pharmacy stock
GET /api/hospitals/pharmacy-stock/

# Submit claim
POST /api/hospitals/submit-claim/

# Get hospital reports
GET /api/hospitals/reports/
```

#### Employer APIs
```bash
# Register employees (bulk)
POST /api/employers/register-employees/

# Submit contributions
POST /api/employers/submit-contributions/

# Get contribution reports
GET /api/employers/reports/
```

## 🔐 Security Features

### Data Protection
- **End-to-end encryption** for sensitive health and payment data
- **HTTPS enforcement** in production
- **Input validation** and sanitization
- **SQL injection protection** via Django ORM
- **CSRF protection** enabled

### Authentication & Authorization
- **JWT tokens** for API authentication
- **Role-based access control** (Member, Hospital, Employer, Admin)
- **OTP verification** for critical operations
- **Session management** with Redis

### Audit Trail
- **Complete audit logging** of all system actions
- **IP address tracking** and user agent logging
- **Fraud detection** algorithms for unusual patterns
- **Data integrity** checks and validation

## 📊 Database Schema

### Core Models Overview
- **User**: Custom user model with role-based types
- **SHAMember**: Member registration and profile data
- **Hospital**: Healthcare provider information
- **Employer**: Company registration and employee management
- **Contribution**: Payment tracking and M-Pesa integration
- **HospitalVisit**: Patient visit records with OTP verification
- **Prescription**: Medicine prescriptions and dispensing
- **Claim**: Hospital reimbursement claims
- **OTP**: Security verification codes
- **AuditLog**: System activity tracking

### Relationships
```
User (1:1) → SHAMember, Hospital, Employer
SHAMember (1:N) → Contributions, HospitalVisits
Hospital (1:N) → HospitalVisits, Claims, PharmacyStock
Prescription (1:N) → PrescriptionItems
HospitalVisit (1:N) → Prescriptions, Claims
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test members
python manage.py test hospitals

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage html
```

### Test Data
```bash
# Load test fixtures
python manage.py loaddata fixtures/test_data.json

# Create test users
python manage.py create_test_users
```

## 📈 Monitoring & Logging

### Logging Configuration
The platform uses structured logging:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/sha_platform.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'django': {'handlers': ['file'], 'level': 'INFO'},
        'sha_platform': {'handlers': ['file'], 'level': 'DEBUG'},
    }
}
```

### Key Metrics to Monitor
- **API response times**
- **Database query performance**
- **OTP generation/verification rates**
- **Failed authentication attempts**
- **Contribution processing success rates**
- **Claim processing times**

## 🚀 Deployment

### Production Requirements
- **Web Server**: Nginx + Gunicorn
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis cluster
- **Task Queue**: Celery with Redis broker
- **Storage**: AWS S3 for media files
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up -d --scale web=3 --scale worker=2
```

### Environment Variables (Production)
```bash
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📚 Documentation

### Code Documentation
```bash
# Generate API documentation
pip install drf-yasg
python manage.py collectstatic
# Visit /swagger/ or /redoc/ for API docs
```

### Additional Resources
- **Admin Portal**: `/admin/` - Django admin interface
- **API Documentation**: `/api/docs/` - Interactive API documentation
- **Health Check**: `/health/` - System status endpoint
- **Metrics**: `/metrics/` - Prometheus metrics endpoint

## 🐛 Troubleshooting

### Common Issues

#### 1. M-Pesa Integration Issues
```bash
# Check M-Pesa credentials
python manage.py test_mpesa_connection

# Verify callback URLs are accessible
python manage.py check_mpesa_callbacks
```

#### 2. OTP Delivery Issues
```bash
# Test SMS service
python manage.py test_sms_service

# Check email configuration
python manage.py sendtestemail your-email@example.com
```

#### 3. Database Performance
```bash
# Check slow queries
python manage.py check_db_performance

# Optimize database
python manage.py optimize_db
```

#### 4. Celery Task Issues
```bash
# Check Celery workers
celery -A sha_platform inspect active

# Purge failed tasks
celery -A sha_platform purge
```

## 🤝 Contributing

### Development Workflow
1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/your-feature`
3. **Write tests** for new functionality
4. **Follow PEP 8** coding standards
5. **Update documentation** as needed
6. **Submit pull request** with detailed description

### Code Style
```bash
# Install development dependencies
pip install black flake8 isort pre-commit

# Set up pre-commit hooks
pre-commit install

# Format code
black .
isort .
flake8 .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Getting Help
- **Documentation**: Check this README and inline code documentation
- **Issues**: Submit bug reports via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: support@shaplatform.ke

### Contact Information
- **Project Lead**: [Your Name] (your.email@example.com)
- **Technical Lead**: [Tech Lead] (tech.lead@example.com)
- **SHA Coordinator**: [SHA Contact] (sha.contact@health.go.ke)

## 🗺️ Roadmap

### Phase 1 (Completed)
- ✅ Basic member registration and SHA number generation
- ✅ Hospital portal with OTP verification
- ✅ Basic claims processing
- ✅ Admin portal for approvals

### Phase 2 (Current)
- 🔄 Mobile app development (React Native)
- 🔄 Advanced fraud detection algorithms
- 🔄 Real-time analytics dashboard
- 🔄 Bulk data migration tools

### Phase 3 (Planned)
- 📋 Integration with existing hospital systems (HL7 FHIR)
- 📋 Telemedicine module
- 📋 AI-powered claim verification
- 📋 Blockchain integration for secure records
- 📋 Multi-language support (English, Swahili)

## 📊 Performance Benchmarks

### Expected Performance (with optimization)
- **API Response Time**: < 200ms (95th percentile)
- **Database Queries**: < 100ms average
- **OTP Generation**: < 5 seconds
- **File Upload**: 10MB files in < 30 seconds
- **Concurrent Users**: 1000+ simultaneous users
- **Daily Transactions**: 100,000+ contributions/claims

---

**Built By Steve  for the people of Kenya**

*Empowering universal health coverage through digital innovation*