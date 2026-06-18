from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    verification_answer = forms.CharField(
        required=False,
        label="Private verification answer",
        help_text="Keep this hidden. Claimants must provide this answer when they claim the item.",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )

    class Meta:
        model = Item
        fields = (
            "title",
            "description",
            "category",
            "location",
            "event_date",
            "image",
            "verification_question",
        )

    def save(self, commit=True):
        item = super().save(commit=False)
        verification_answer = self.cleaned_data.get("verification_answer", "")
        image = self.cleaned_data.get("image")
        if verification_answer:
            item.set_verification_answer(verification_answer)
        if image:
            item.store_image_file(image)
        if commit:
            item.save()
            self.save_m2m()
        return item


class AdminItemForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    verification_answer = forms.CharField(
        required=False,
        label="Private verification answer",
        help_text="Leave blank to keep the existing answer.",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )

    class Meta:
        model = Item
        fields = (
            "report_type",
            "title",
            "description",
            "category",
            "location",
            "event_date",
            "image",
            "verification_question",
            "status",
            "reported_by",
        )

    def save(self, commit=True):
        item = super().save(commit=False)
        verification_answer = self.cleaned_data.get("verification_answer", "")
        image = self.cleaned_data.get("image")
        if verification_answer:
            item.set_verification_answer(verification_answer)
        if image:
            item.store_image_file(image)
        if commit:
            item.save()
            self.save_m2m()
        return item


class ClaimForm(forms.Form):
    verification_answer = forms.CharField(
        required=False,
        label="Verification answer",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
    proof_details = forms.CharField(
        label="Ownership proof",
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Describe details only the owner would know, such as marks, contents, serial digits, or documents you can show at pickup.",
                "rows": 4,
            }
        ),
    )


class MessageForm(forms.Form):
    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Write a message...",
                "rows": 3,
            }
        ),
        max_length=2000,
    )
