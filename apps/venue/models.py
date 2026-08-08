from django.db import models

from apps.core.models import TenantModel, TimeStampedModel


class Venue(TimeStampedModel):
    """An event venue, with the profile and policy data used by the AI sales agent."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    whatsapp_number = models.CharField(max_length=20, unique=True)
    whatsapp_phone_number_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    timezone = models.CharField(max_length=64, default='America/Sao_Paulo')
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    parking_info = models.TextField(blank=True)
    payment_policy = models.TextField(blank=True)
    cancellation_policy = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class OpeningHours(TimeStampedModel):
    """A venue's opening hours for a single weekday."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, 'Segunda-feira'
        TUESDAY = 1, 'Terça-feira'
        WEDNESDAY = 2, 'Quarta-feira'
        THURSDAY = 3, 'Quinta-feira'
        FRIDAY = 4, 'Sexta-feira'
        SATURDAY = 5, 'Sábado'
        SUNDAY = 6, 'Domingo'

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='opening_hours')
    weekday = models.IntegerField(choices=Weekday.choices)
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('venue', 'weekday')
        ordering = ['weekday']

    def __str__(self):
        return f'{self.venue} - {self.get_weekday_display()}'


class EventType(TenantModel):
    """A category of event a venue hosts (e.g. wedding, birthday), with guest count limits."""

    name = models.CharField(max_length=100)
    min_guests = models.PositiveIntegerField(null=True, blank=True)
    max_guests = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('venue', 'name')

    def __str__(self):
        return self.name


class Package(TenantModel):
    """A priced bundle of services a venue offers for a given event type."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    event_type = models.ForeignKey(
        EventType, on_delete=models.SET_NULL, null=True, blank=True, related_name='packages',
    )

    def __str__(self):
        return self.name


class Menu(TenantModel):
    """A food/drink menu a venue offers, made up of MenuItems."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price_per_person = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """A single dish or drink belonging to a Menu."""

    class Category(models.TextChoices):
        STARTER = 'starter', 'Entrada'
        MAIN = 'main', 'Prato principal'
        DESSERT = 'dessert', 'Sobremesa'
        DRINK = 'drink', 'Bebida'

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)

    def __str__(self):
        return self.name


class DecorationOption(TenantModel):
    """An optional decoration add-on a venue offers, with its price."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name


class FAQ(TenantModel):
    """A frequently asked question and answer shown to venue visitors."""

    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class Document(TenantModel):
    """A file (e.g. contract, brochure) uploaded for a venue."""

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='venue_documents/')

    def __str__(self):
        return self.title


class Image(TenantModel):
    """A photo uploaded for a venue's gallery."""

    image = models.ImageField(upload_to='venue_images/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.caption or f'Image {self.pk}'
