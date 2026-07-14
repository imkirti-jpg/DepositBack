import sys
import os
import uuid
import asyncio
import unittest
from datetime import datetime, timezone
from sqlalchemy import select, delete

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.users import User
from app.models.property import Property, PropertyStatus
from app.services.property_service import PropertyService
from fastapi import HTTPException

class TestPropertyDeletion(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.db = SessionLocal()
        
        # Create test users
        self.owner = User(
            id=uuid.uuid4(),
            full_name="Owner User",
            city="Test City"
        )
        self.other_user = User(
            id=uuid.uuid4(),
            full_name="Other User",
            city="Test City"
        )
        
        self.db.add_all([self.owner, self.other_user])
        await self.db.commit()

        # Create test property owned by owner
        self.property = Property(
            id=uuid.uuid4(),
            user_id=self.owner.id,
            label="Owner Test Property",
            deposit_amount=1200.0,
            status=PropertyStatus.active
        )
        self.db.add(self.property)
        await self.db.commit()

    async def asyncTearDown(self):
        # Clean up database records
        await self.db.execute(delete(Property).where(Property.id == self.property.id))
        await self.db.execute(delete(User).where(User.id.in_([self.owner.id, self.other_user.id])))
        await self.db.commit()
        await self.db.close()

    async def test_owner_can_delete_and_hides_from_list(self):
        # Verify property is in owner's property list initially
        props = await PropertyService.list_properties(self.db, self.owner)
        prop_ids = [p.id for p in props]
        self.assertIn(self.property.id, prop_ids)

        # Verify other user gets 404 / ownership failure when trying to get/delete
        with self.assertRaises(HTTPException) as ctx:
            await PropertyService.delete_property(self.db, self.property.id, self.other_user)
        self.assertEqual(ctx.exception.status_code, 404)

        # Owner performs soft deletion
        await PropertyService.delete_property(self.db, self.property.id, self.owner)

        # Refresh database and verify soft delete columns are updated
        result = await self.db.execute(select(Property).where(Property.id == self.property.id))
        deleted_prop = result.scalar_one()
        self.assertIsNotNone(deleted_prop.deleted_at)
        self.assertEqual(deleted_prop.deleted_by, self.owner.id)

        # Verify property is no longer returned in normal list queries
        props_after = await PropertyService.list_properties(self.db, self.owner)
        prop_ids_after = [p.id for p in props_after]
        self.assertNotIn(self.property.id, prop_ids_after)

        # Verify get_property throws 404 for deleted property
        with self.assertRaises(HTTPException) as ctx:
            await PropertyService.get_property(self.db, self.property.id, self.owner)
        self.assertEqual(ctx.exception.status_code, 404)

if __name__ == "__main__":
    unittest.main()
