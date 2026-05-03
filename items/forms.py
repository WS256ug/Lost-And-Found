from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Item
        fields = ("title", "description", "category", "location", "event_date", "image")


class AdminItemForm(forms.ModelForm):
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
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
            "status",
            "reported_by",
        )
