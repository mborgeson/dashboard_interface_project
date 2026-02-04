"""Test data factories using factory_boy.

Provides factories for generating test data:
- UserFactory: Create test users with realistic data
- DealFactory: Create test deals with various stages
- PropertyFactory: Create test properties
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

import factory
from factory import fuzzy

from app.core.security import get_password_hash
from app.models import Deal, DealStage, Property, User


class UserFactory(factory.Factory):
    """Factory for creating test User instances."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@bandrcapital-test.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    hashed_password = factory.LazyFunction(lambda: get_password_hash("testpassword123"))
    role = fuzzy.FuzzyChoice(["admin", "analyst", "viewer"])
    is_active = True
    is_verified = True

    @factory.lazy_attribute
    def full_name(self):
        """Generate full name from first and last name."""
        return f"{self.first_name} {self.last_name}"


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""

    role = "admin"
    email = factory.Sequence(lambda n: f"admin{n}@bandrcapital-test.com")


class AnalystUserFactory(UserFactory):
    """Factory for creating analyst users."""

    role = "analyst"
    email = factory.Sequence(lambda n: f"analyst{n}@bandrcapital-test.com")


class DealFactory(factory.Factory):
    """Factory for creating test Deal instances."""

    class Meta:
        model = Deal

    name = factory.Sequence(lambda n: f"Test Deal {n}")
    deal_type = fuzzy.FuzzyChoice(["acquisition", "disposition", "refinance"])
    stage = fuzzy.FuzzyChoice(list(DealStage))
    priority = fuzzy.FuzzyChoice(["low", "medium", "high", "urgent"])

    # Financial data
    asking_price = fuzzy.FuzzyDecimal(5000000, 50000000, precision=2)
    offer_price = factory.LazyAttribute(
        lambda obj: obj.asking_price * Decimal("0.95") if obj.asking_price else None
    )
    projected_irr = fuzzy.FuzzyDecimal(10, 25, precision=2)

    # Relationships
    assigned_user_id = None
    property_id = None

    # Text fields
    notes = factory.Faker("paragraph", nb_sentences=2)
    investment_thesis = factory.Faker("paragraph", nb_sentences=3)


class InitialReviewDealFactory(DealFactory):
    """Factory for deals in Initial Review stage."""

    stage = DealStage.INITIAL_REVIEW
    name = factory.Sequence(lambda n: f"Initial Review Deal {n}")


class ActiveReviewDealFactory(DealFactory):
    """Factory for deals in Active Review stage."""

    stage = DealStage.ACTIVE_REVIEW
    name = factory.Sequence(lambda n: f"Active Review Deal {n}")


class ClosedDealFactory(DealFactory):
    """Factory for closed deals."""

    stage = DealStage.CLOSED
    name = factory.Sequence(lambda n: f"Closed Deal {n}")
    final_price = factory.LazyAttribute(
        lambda obj: obj.offer_price if obj.offer_price else obj.asking_price
    )


class PropertyFactory(factory.Factory):
    """Factory for creating test Property instances."""

    class Meta:
        model = Property

    name = factory.Sequence(lambda n: f"Test Property {n}")
    property_type = fuzzy.FuzzyChoice(["multifamily", "office", "retail", "industrial"])

    # Location
    address = factory.Faker("street_address")
    city = fuzzy.FuzzyChoice(["Phoenix", "Scottsdale", "Tempe", "Mesa", "Tucson"])
    state = "AZ"
    zip_code = factory.Sequence(lambda n: f"8500{n % 10}")
    market = "Phoenix Metro"

    # Property details
    total_units = fuzzy.FuzzyInteger(50, 300)
    year_built = fuzzy.FuzzyInteger(1990, 2023)

    # Financial metrics
    occupancy_rate = fuzzy.FuzzyDecimal(85, 99, precision=1)
    avg_rent_per_unit = fuzzy.FuzzyDecimal(1000, 2500, precision=2)
    noi = fuzzy.FuzzyDecimal(500000, 5000000, precision=2)
    cap_rate = fuzzy.FuzzyDecimal(4.5, 7.5, precision=2)


class MultifamilyPropertyFactory(PropertyFactory):
    """Factory for multifamily properties."""

    property_type = "multifamily"
    name = factory.Sequence(lambda n: f"Apartments {n}")
    total_units = fuzzy.FuzzyInteger(100, 400)


class OfficePropertyFactory(PropertyFactory):
    """Factory for office properties."""

    property_type = "office"
    name = factory.Sequence(lambda n: f"Office Park {n}")
    total_sf = fuzzy.FuzzyInteger(50000, 200000)
    total_units = None


class RetailPropertyFactory(PropertyFactory):
    """Factory for retail properties."""

    property_type = "retail"
    name = factory.Sequence(lambda n: f"Retail Center {n}")
    total_sf = fuzzy.FuzzyInteger(20000, 100000)
    total_units = None


# =============================================================================
# Factory Helper Functions
# =============================================================================


def create_user_batch(count: int = 5, **kwargs) -> list:
    """Create a batch of users."""
    return UserFactory.build_batch(count, **kwargs)


def create_deal_batch(count: int = 5, **kwargs) -> list:
    """Create a batch of deals."""
    return DealFactory.build_batch(count, **kwargs)


def create_property_batch(count: int = 5, **kwargs) -> list:
    """Create a batch of properties."""
    return PropertyFactory.build_batch(count, **kwargs)


def create_deal_pipeline() -> dict:
    """Create a full deal pipeline with deals at each stage."""
    pipeline = {}
    for stage in DealStage:
        pipeline[stage.value] = DealFactory.build_batch(
            random.randint(1, 5), stage=stage
        )
    return pipeline
