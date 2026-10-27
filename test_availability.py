import sqlite3

def is_resource_available(resource_id, date, start_time, end_time):
    conn = sqlite3.connect('database.db')
    query = """SELECT id FROM allocations
               WHERE resource_id = ? AND date = ? AND status != 'Cancelled'
               AND start_time < ? AND end_time > ?"""
    cursor = conn.execute(query, [resource_id, date, end_time, start_time])
    conflict = cursor.fetchone()
    conn.close()
    return conflict is None

print("=== AVAILABILITY ALGORITHM TESTS ===")

# Test 1: Overlap - Bob Smith has Projector 1 (id=3) on 2026-09-24 10:00-12:00
# New request 11:00-13:00 should CONFLICT
result = is_resource_available(3, '2026-09-24', '11:00', '13:00')
status = "PASS" if not result else "FAIL"
print(f"Test 1 - Overlap (11:00-13:00 vs existing 10:00-12:00) => CONFLICT expected: {status} | Available={result}")

# Test 2: Adjacent - 12:00-14:00 after existing 10:00-12:00 should NOT conflict
result = is_resource_available(3, '2026-09-24', '12:00', '14:00')
status = "PASS" if result else "FAIL"
print(f"Test 2 - Adjacent (12:00-14:00 after 10:00-12:00) => NO CONFLICT expected: {status} | Available={result}")

# Test 3: Different resource, no allocation
result = is_resource_available(1, '2026-09-24', '10:00', '12:00')
status = "PASS" if result else "FAIL"
print(f"Test 3 - Computer Lab 1 same time (no allocation) => AVAILABLE expected: {status} | Available={result}")

# Test 4: Frank Wilson has Classroom 101 (id=8) 08:00-10:00
# Request 09:00-11:00 should CONFLICT
result = is_resource_available(8, '2026-09-24', '09:00', '11:00')
status = "PASS" if not result else "FAIL"
print(f"Test 4 - Overlap (09:00-11:00 vs existing 08:00-10:00) => CONFLICT expected: {status} | Available={result}")

# Test 5: Before existing - 07:00-08:00 should NOT conflict with 08:00-10:00
result = is_resource_available(8, '2026-09-24', '07:00', '08:00')
status = "PASS" if result else "FAIL"
print(f"Test 5 - Before existing (07:00-08:00 vs 08:00-10:00) => NO CONFLICT expected: {status} | Available={result}")

print("=== DONE ===")
