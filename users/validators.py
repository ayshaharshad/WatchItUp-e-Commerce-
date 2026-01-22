"""
Custom validators for user profile fields
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


class AlphabeticValidator:
    """Validate that a string contains only alphabetic characters and spaces"""
    
    def __call__(self, value):
        if not value:
            return
        
        # Allow only letters and spaces
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise ValidationError(
                'Only alphabetic characters and spaces are allowed.',
                code='invalid_alphabetic'
            )
        
        # Check for excessive spaces
        if '  ' in value:
            raise ValidationError(
                'Consecutive spaces are not allowed.',
                code='consecutive_spaces'
            )
        
        # Check if starts or ends with space
        if value.startswith(' ') or value.endswith(' '):
            raise ValidationError(
                'Name cannot start or end with a space.',
                code='boundary_spaces'
            )
    
    def deconstruct(self):
        """Return a 4-tuple for Django migrations serialization"""
        return (
            'users.validators.AlphabeticValidator',
            (),
            {}
        )
    
    def __eq__(self, other):
        return isinstance(other, self.__class__)


class UsernameValidator:
    """Validate username format - only letters, numbers, and underscore"""
    
    def __call__(self, value):
        if not value:
            return
        
        # Only allow letters, numbers, and underscore
        if not re.match(r"^[a-zA-Z0-9@.+_-]+$", value):
            raise ValidationError(
                'Username can only contain letters, numbers, and underscore (_).',
                code='invalid_username'
            )
        
        # Minimum length
        if len(value) < 3:
            raise ValidationError(
                'Username must be at least 3 characters long.',
                code='username_too_short'
            )
        
        # Maximum length
        if len(value) > 30:
            raise ValidationError(
                'Username must not exceed 30 characters.',
                code='username_too_long'
            )
        
        # Must start with letter or number
        if value[0] == '_':
            raise ValidationError(
                'Username cannot start with an underscore.',
                code='username_starts_underscore'
            )
        
        # Must end with letter or number
        if value[-1] == '_':
            raise ValidationError(
                'Username cannot end with an underscore.',
                code='username_ends_underscore'
            )
        
        # Check for consecutive underscores
        if '__' in value:
            raise ValidationError(
                'Username cannot contain consecutive underscores.',
                code='consecutive_underscores'
            )
        
        # Check if username is only numbers
        if value.isdigit():
            raise ValidationError(
                'Username cannot contain only numbers.',
                code='username_only_numbers'
            )
    
    def deconstruct(self):
        """Return a 4-tuple for Django migrations serialization"""
        return (
            'users.validators.UsernameValidator',
            (),
            {}
        )
    
    def __eq__(self, other):
        return isinstance(other, self.__class__)


class PhoneNumberValidator:
    """Validate Indian phone number - exactly 10 digits"""
    
    def __call__(self, value):
        if not value:
            return
        
        # Remove spaces and common separators
        cleaned = re.sub(r'[\s\-\(\)]', '', value)
        
        # Check if only digits
        if not cleaned.isdigit():
            raise ValidationError(
                'Phone number must contain only digits.',
                code='invalid_phone_format'
            )
        
        # Check exact length (10 digits for Indian numbers)
        if len(cleaned) != 10:
            raise ValidationError(
                'Phone number must be exactly 10 digits.',
                code='invalid_phone_length'
            )
        
        # Check if starts with valid digit (Indian numbers start with 6-9)
        if cleaned[0] not in ['6', '7', '8', '9']:
            raise ValidationError(
                'Phone number must start with 6, 7, 8, or 9.',
                code='invalid_phone_start'
            )
        
        # Check if all digits are the same (e.g., 9999999999)
        if len(set(cleaned)) == 1:
            raise ValidationError(
                'Phone number cannot have all identical digits.',
                code='invalid_phone_pattern'
            )
    
    def deconstruct(self):
        """Return a 4-tuple for Django migrations serialization"""
        return (
            'users.validators.PhoneNumberValidator',
            (),
            {}
        )
    
    def __eq__(self, other):
        return isinstance(other, self.__class__)


# Regex validators for form fields
username_regex_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9@.+_-]+$',
    message='Username can only contain letters, numbers, and underscore (_).',
    code='invalid_username'
)

phone_regex_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='Enter a valid 10-digit phone number starting with 6, 7, 8, or 9.',
    code='invalid_phone'
)

name_regex_validator = RegexValidator(
    regex=r'^[a-zA-Z\s]+$',
    message='Only alphabetic characters and spaces are allowed.',
    code='invalid_name'
)