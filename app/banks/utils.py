import json
from sqlalchemy.future import select
from ..models import Bank
from ..database import async_session

async def import_initial_banks():
    """Import initial banks during app initialization."""
    async with async_session() as db:
        # Check if any banks exist
        result = await db.execute(select(Bank))
        if result.scalars().first() is not None:
            print("Banks already exist. Skipping initial import.")
            return

        try:
            with open('app/banks/banks.json', 'r') as file:
                data = json.load(file)

            # Process both banks and DTMs
            all_entries = data.get('banks', []) + data.get('dtms', [])
            
            created = 0
            updated = 0

            for entry in all_entries:
                # Check existing by paybill_no
                result = await db.execute(
                    select(Bank).filter_by(paybill_no=entry['paybill_no'])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    if existing.name != entry['name']:
                        existing.name = entry['name']
                        updated += 1
                else:
                    db.add(Bank(
                        name=entry['name'],
                        paybill_no=entry['paybill_no']
                    ))
                    created += 1

            await db.commit()
            print(f"Successfully imported {created} banks, updated {updated}")

        except Exception as e:
            await db.rollback()
            print(f"Error importing banks: {str(e)}")
            raise