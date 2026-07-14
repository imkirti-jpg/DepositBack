import uuid
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.evidence import Evidence, EvidencePhase
from app.api.v1.evidence_router import format_evidence_response
from app.schemas.evidence import EvidenceResponse

def test_evidence_serialization():
    # Construct mock SQLAlchemy model instance
    mock_ev = Evidence(
        id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        phase=EvidencePhase.move_in,
        room_label="Kitchen",
        file_url="http://supabase.com/evidence/123.jpg",
        file_hash="abcde12345",
        display_name="Move-in Kitchen Photo 1",
        category="move_in",
        sort_order=1,
        notes="Clean counter",
        mime_type="image/jpeg",
        file_size=50000,
        width=1024,
        height=768,
        captured_at=datetime.now(timezone.utc),
        deleted_at=None,
        deleted_by=None,
        created_at=datetime.now(timezone.utc),
    )
    
    # Serialize it
    response = format_evidence_response(mock_ev)
    
    # Assertions
    assert isinstance(response, EvidenceResponse)
    assert response.id == mock_ev.id
    assert response.uploaded_at == mock_ev.created_at
    assert response.display_name == mock_ev.display_name
    assert response.category == "move_in"
    print("Serialization check: PASSED")

if __name__ == "__main__":
    test_evidence_serialization()
