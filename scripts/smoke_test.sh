#!/usr/bin/env bash
set -euo pipefail

# DeptHub Smoke Test Script
# Usage: ./scripts/smoke_test.sh [BASE_URL]
# Example: ./scripts/smoke_test.sh http://localhost:8000

BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}" # Strip trailing slash if present

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=================================================="
echo "Running DeptHub Smoke Test against: $BASE_URL"
echo "=================================================="

FAILED=0

check_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    local match_pattern="$4"

    printf "Checking %-30s ... " "$name"

    # Make request capturing HTTP code and response body
    local response
    local http_code
    response=$(curl -s -w "\n%{http_code}" "$url" || true)
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ne "$expected_code" ]; then
        printf "${RED}FAIL${NC} (expected HTTP %d, got %s)\n" "$expected_code" "$http_code"
        FAILED=1
        return
    fi

    if [ -n "$match_pattern" ]; then
        if ! echo "$body" | grep -q "$match_pattern"; then
            printf "${RED}FAIL${NC} (missing pattern '%s')\n" "$match_pattern"
            FAILED=1
            return
        fi
    fi

    printf "${GREEN}PASS${NC} (HTTP %s)\n" "$http_code"
}

# 1. Healthcheck
check_endpoint "GET /health" "$BASE_URL/health" 200 '"status":"ok"'

# 2. Public Notice Board Home Page
check_endpoint "GET / (Notice Board)" "$BASE_URL/" 200 "Notice Board"

# 3. Notice Board Search Filtering
check_endpoint "GET /?q=test (Search)" "$BASE_URL/?q=test" 200 "Notice Board"

# 4. Weekly Routine Page
check_endpoint "GET /routine" "$BASE_URL/routine" 200 "Weekly Class Routine"

# 5. Today's Routine Page
check_endpoint "GET /today" "$BASE_URL/today" 200 "Class Schedule"

# 6. Upcoming Exams Page
check_endpoint "GET /exams" "$BASE_URL/exams" 200 "Examination Schedule"

# 7. Atom Feed
check_endpoint "GET /feeds/notices.atom" "$BASE_URL/feeds/notices.atom" 200 "<feed"

# 8. iCalendar Feed for Batch 1 (or 404 handled cleanly if empty)
printf "Checking %-30s ... " "GET /feeds/batch/1.ics"
ics_resp=$(curl -s -w "\n%{http_code}" "$BASE_URL/feeds/batch/1.ics" || true)
ics_code=$(echo "$ics_resp" | tail -n1)
ics_body=$(echo "$ics_resp" | sed '$d')

if [ "$ics_code" -eq 200 ]; then
    if echo "$ics_body" | grep -q "BEGIN:VCALENDAR"; then
        printf "${GREEN}PASS${NC} (HTTP 200 VCALENDAR)\n"
    else
        printf "${RED}FAIL${NC} (HTTP 200 but missing BEGIN:VCALENDAR)\n"
        FAILED=1
    fi
elif [ "$ics_code" -eq 404 ]; then
    printf "${GREEN}PASS${NC} (HTTP 404 cleanly returned for unseeded batch 1)\n"
else
    printf "${RED}FAIL${NC} (unexpected HTTP %s)\n" "$ics_code"
    FAILED=1
fi

echo "=================================================="
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All smoke tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Smoke tests failed!${NC}"
    exit 1
fi
