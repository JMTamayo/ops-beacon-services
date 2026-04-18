from pygination.models import PageModel

from app.schemas.device import DeviceRead
from app.schemas.device_entity_assignment import DeviceEntityAssignmentRead
from app.schemas.entity import EntityRead
from app.schemas.measurement import MeasurementRead


class MeasurementPage(PageModel[MeasurementRead]):
    """Paginated list of measurements (pygination ``PageModel``)."""


class DevicePage(PageModel[DeviceRead]):
    """Paginated list of devices."""


class EntityPage(PageModel[EntityRead]):
    """Paginated list of catalog entities."""


class DeviceEntityAssignmentPage(PageModel[DeviceEntityAssignmentRead]):
    """Paginated list of device–entity assignments."""

