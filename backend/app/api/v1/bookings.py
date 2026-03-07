from fastapi import APIRouter, HTTPException

from app.models.booking import ServiceBooking, ServiceBookingCreate

router = APIRouter(prefix="/service", tags=["service"])

# In-memory store for now
_bookings: dict[int, ServiceBooking] = {}
_next_id = 1


@router.get("/bookings", response_model=list[ServiceBooking])
async def list_bookings() -> list[ServiceBooking]:
    return list(_bookings.values())


@router.post("/bookings", response_model=ServiceBooking, status_code=201)
async def create_booking(payload: ServiceBookingCreate) -> ServiceBooking:
    global _next_id
    booking = ServiceBooking(id=_next_id, **payload.model_dump())
    _bookings[_next_id] = booking
    _next_id += 1
    return booking


@router.get("/bookings/{booking_id}", response_model=ServiceBooking)
async def get_booking(booking_id: int) -> ServiceBooking:
    booking = _bookings.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
