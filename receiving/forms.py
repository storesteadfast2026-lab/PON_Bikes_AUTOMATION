from django import forms
from decimal import Decimal
import re
from openpyxl.utils import column_index_from_string, get_column_letter

from .models import Container, ProductCatalog, ProductDefinition, SourceFile


class ContainerForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = ["job_order", "identifier", "customer", "container_date"]
        widgets = {
            "job_order": forms.TextInput(attrs={"placeholder": "Translogic Job Order", "autocomplete": "off"}),
            "identifier": forms.TextInput(attrs={"placeholder": "FDCU0321443", "autocomplete": "off"}),
            "container_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
        labels = {
            "identifier": "Container ID",
            "container_date": "Container date",
            "job_order": "Job Order",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["container_date"].required = True
        self.fields["job_order"].required = True

    def clean_job_order(self):
        value = (self.cleaned_data.get("job_order") or "").strip().upper()
        if self.fields["job_order"].required and not value:
            raise forms.ValidationError("Enter the Translogic Job Order.")
        existing = Container.objects.filter(job_order=value).exclude(pk=self.instance.pk).first() if value else None
        if existing:
            raise forms.ValidationError(
                f"Job Order {value} is already assigned to container {existing.identifier}."
            )
        return value

    def clean_identifier(self):
        value = re.sub(r"\s+", "", (self.cleaned_data.get("identifier") or "").strip().upper())
        return value

    def save(self, commit=True):
        container = super().save(commit=False)
        if self.cleaned_data.get("container_date"):
            container.year = self.cleaned_data["container_date"].year
        if commit:
            container.save()
            self.save_m2m()
        return container


class SourceUploadForm(forms.ModelForm):
    class Meta:
        model = SourceFile
        fields = ["kind", "file"]
        widgets = {"file": forms.FileInput(attrs={"accept": ".xlsx,.xlsm"})}


class ProductCatalogUploadForm(forms.ModelForm):
    class Meta:
        model = ProductCatalog
        fields = ["file"]
        widgets = {"file": forms.FileInput(attrs={"accept": ".xls,.xml,application/vnd.ms-excel"})}


class ProductMovesUploadForm(forms.Form):
    file = forms.FileField(
        label="PRODUCT_MOVES.CSV",
        widget=forms.FileInput(attrs={"accept": ".csv,text/csv"}),
        help_text="Fallback upload when the configured T: drive path is unavailable to Docker.",
    )


class ProductDefinitionForm(forms.ModelForm):
    length_cm = forms.DecimalField(
        label="Length cm",
        min_value=Decimal("0.1"),
        max_digits=8,
        decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "0.1", "step": "0.1", "class": "measure-input", "data-measure": "length"}),
    )
    height_cm = forms.DecimalField(
        label="Height cm",
        min_value=Decimal("0.1"),
        max_digits=8,
        decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "0.1", "step": "0.1", "class": "measure-input", "data-measure": "height"}),
    )
    width_cm = forms.DecimalField(
        label="Width cm",
        min_value=Decimal("0.1"),
        max_digits=8,
        decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "0.1", "step": "0.1", "class": "measure-input", "data-measure": "width"}),
    )

    class Meta:
        model = ProductDefinition
        fields = ["long_code", "short_name", "full_name", "length_cm", "height_cm", "width_cm", "weight_kg"]
        widgets = {
            "short_name": forms.TextInput(attrs={"maxlength": 30, "class": "product-name-input"}),
            "full_name": forms.TextInput(attrs={"class": "product-full-name-input"}),
            "weight_kg": forms.NumberInput(attrs={"min": "0.001", "step": "0.001", "class": "measure-input", "data-measure": "weight"}),
        }
        labels = {
            "full_name": "Long name",
        }
        help_texts = {
            "short_name": "Suggested by the historical product-master dictionary; review it before saving.",
        }

    def __init__(self, *args, **kwargs):
        lock_source_fields = bool(kwargs.pop("lock_source_fields", False))
        super().__init__(*args, **kwargs)
        # ProductDefinitionForm is shared by other workflows. Source-derived
        # fields are locked only when Product Check explicitly requests it.
        if lock_source_fields:
            for field_name in ("long_code", "full_name"):
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs["tabindex"] = "-1"
                self.fields[field_name].widget.attrs["aria-readonly"] = "true"
        if self.instance and self.instance.pk:
            self.initial.setdefault("length_cm", Decimal(self.instance.length_mm) / Decimal("10"))
            self.initial.setdefault("height_cm", Decimal(self.instance.height_mm) / Decimal("10"))
            self.initial.setdefault("width_cm", Decimal(self.instance.width_mm) / Decimal("10"))

    def clean_short_name(self):
        value = self.cleaned_data["short_name"].strip()
        if len(value) > 30:
            raise forms.ValidationError("The Translogic name in column C can contain at most 30 characters.")
        return value

    def save(self, commit=True):
        product = super().save(commit=False)
        # Operators enter centimetres, while Translogic and the database use millimetres.
        product.length_mm = int(self.cleaned_data["length_cm"] * Decimal("10"))
        product.height_mm = int(self.cleaned_data["height_cm"] * Decimal("10"))
        product.width_mm = int(self.cleaned_data["width_cm"] * Decimal("10"))
        if commit:
            product.save()
            self.save_m2m()
        return product


class ImportMappingForm(forms.Form):
    sheet_name = forms.ChoiceField(label="Worksheet")
    start_row = forms.IntegerField(min_value=1, initial=2, label="First data row")
    start_column = forms.CharField(max_length=3, required=False, initial="A", label="First preview column")
    row_step = forms.IntegerField(min_value=1, max_value=20, initial=1, label="Read every N rows")
    code_column = forms.CharField(max_length=3, required=False, initial="", label="Bike code column")
    long_code_column = forms.CharField(max_length=3, required=False, label="LongCode column")
    description_column = forms.CharField(max_length=3, required=False, label="Description column")
    quantity_column = forms.CharField(max_length=3, required=False, label="Quantity column")
    container_column = forms.CharField(max_length=3, required=False, label="Container column")
    coloured_rows_only = forms.BooleanField(required=False, label="Only rows with a coloured fill")
    required_fill_signature = forms.CharField(
        max_length=120,
        required=False,
        label="Required fill (automatically detected)",
        help_text="Leave the suggested value unchanged when only the green client rows are received.",
    )
    location_stream = forms.BooleanField(
        required=False,
        label="Scanner file: T9999 rows set the pallet/location for following bikes",
    )
    save_profile = forms.BooleanField(required=False, label="Save this mapping for the customer")
    profile_name = forms.CharField(max_length=100, required=False, label="Profile name")

    def __init__(self, *args, sheets=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sheet_name"].choices = [(name, name) for name in (sheets or [])]

    def clean_start_column(self):
        value = (self.cleaned_data.get("start_column") or "A").strip().upper()
        try:
            return get_column_letter(column_index_from_string(value))
        except ValueError as exc:
            raise forms.ValidationError("Enter a valid Excel column, for example A or D.") from exc

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("save_profile") and not cleaned.get("profile_name"):
            self.add_error("profile_name", "Enter a profile name before saving the mapping.")
        for field in ["code_column", "long_code_column", "description_column", "quantity_column", "container_column"]:
            value = (cleaned.get(field) or "").strip().upper()
            if value and (not value.isalpha() or len(value) > 3):
                self.add_error(field, "Use an Excel column letter, for example A, D or AA.")
            cleaned[field] = value
        if not cleaned.get("code_column") and not cleaned.get("long_code_column"):
            self.add_error("code_column", "Enter a Bike code column or a LongCode column.")
        return cleaned
