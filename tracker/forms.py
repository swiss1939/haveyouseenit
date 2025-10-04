# tracker/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Profile, InviteCode, Friendship

# --- NEW FORM FOR UPDATING USER DETAILS ---
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email, is_active=True).exclude(pk=self.instance.pk).exists():
            raise ValidationError('An active account with this email address already exists.')
        return email
# --- END NEW FORM ---


class CustomUserCreationForm(UserCreationForm):
    invite_code = forms.CharField(
        max_length=8,
        required=True,
        label='Invite Code',
        help_text='An invite code is required to create an account.'
    )
    email = forms.EmailField(required=True, help_text='Required. Used for account recovery and communication.')
    first_name = forms.CharField(max_length=50, required=True, label='First Name')
    last_name = forms.CharField(max_length=50, required=True, label='Last Name')
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Date of Birth'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'invite_code',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email__iexact=email, is_active=True).exists():
                raise ValidationError("An active account with this email address already exists.")
        return email

    def clean_invite_code(self):
        code_str = self.cleaned_data.get('invite_code').upper();
        try:
            invite_code = InviteCode.objects.get(code=code_str)
            if invite_code.used_by is not None: raise ValidationError("This invite code has already been used.")
        except InviteCode.DoesNotExist: raise ValidationError("Invalid invite code.")
        self.cleaned_data['invite_code_obj'] = invite_code
        return code_str

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        user.email = self.cleaned_data["email"]; user.first_name = self.cleaned_data["first_name"]; user.last_name = self.cleaned_data["last_name"]
        user.profile.date_of_birth = self.cleaned_data["date_of_birth"]
        invite_code = self.cleaned_data['invite_code_obj']
        invite_code.used_by = user; invite_code.used_at = timezone.now()
        if invite_code.generated_by:
            inviter = invite_code.generated_by
            Friendship.objects.create(from_user=inviter, to_user=user, status=Friendship.Status.ACCEPTED)
            Friendship.objects.create(from_user=user, to_user=inviter, status=Friendship.Status.ACCEPTED)
        if commit: user.save(); user.profile.save(); invite_code.save()
        return user