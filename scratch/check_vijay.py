import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

VIJAY_ID    = 'bb553391-e586-4324-8e0f-04367815a006'
VIJAY_FARM  = 'b1311e1a-6a8a-4df9-8946-dc9ba24dbc49'

async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    print('=== VIJAY USER ===')
    row = await conn.fetchrow('SELECT id, name, email, phone FROM users WHERE id = $1', VIJAY_ID)
    print(dict(row))

    print('\n=== VIJAY FARM ===')
    farm = await conn.fetchrow('SELECT id, name, location, latitude, longitude FROM farms WHERE id = $1', VIJAY_FARM)
    print(dict(farm))

    print('\n=== VIJAY DEVICES ===')
    devices = await conn.fetch(
        'SELECT id, mac_address, node_label, device_uid, status, is_master, pairing_code, last_seen_at '
        'FROM devices WHERE farm_id = $1', VIJAY_FARM
    )
    for d in devices:
        print(dict(d))

    print('\n=== VIJAY ZONES ===')
    zones = await conn.fetch(
        'SELECT z.id, z.name, z.crop_type, z.status FROM zones z WHERE z.farm_id = $1', VIJAY_FARM
    )
    for z in zones:
        print(dict(z))

    await conn.close()

asyncio.run(main())
