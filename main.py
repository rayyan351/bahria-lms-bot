# main.py - Bahria LMS Bot for Render
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
import ssl
from datetime import datetime, timedelta
import os
from flask import Flask
import threading

print("🚀 Bahria LMS Bot Starting...")

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Bahria LMS Bot is Running!<br><br>📚 Monitoring your assignments 24/7<br>✅ Health: <a href='/health'>Check Health</a>"

@app.route('/health')
def health():
    return "✅ Bot is healthy and running!"

@app.route('/status')
def status():
    return f"🕒 Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>🚀 Bot Status: ACTIVE"

@app.route('/debug')
def debug():
    return f"""
    <h1>Bot Debug Info</h1>
    <p>Current Time: {datetime.now()}</p>
    <p>Last Check Should Have Been: ~{datetime.now().strftime('%H:%M')}</p>
    <p>Next Check Should Be: ~{(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')}</p>
    <p>Status: 🟢 Running</p>
    <a href="/health">Health Check</a> | 
    <a href="/status">Status</a>
    """



class ReplitLMSBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.base_cms_url = "https://cms.bahria.edu.pk"
        self.base_lms_url = "https://lms.bahria.edu.pk"
        self.setup_database()

    def setup_database(self):
        self.conn = sqlite3.connect('lms_tracker.db', check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT, course_name TEXT, assignment_number TEXT,
                assignment_title TEXT, assignment_file_available BOOLEAN,
                marks_available BOOLEAN, marks_text TEXT, 
                returned_submission_available BOOLEAN, deadline TEXT,
                first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        print("✅ Database setup complete")

    def set_all_cookies(self):
        # CMS Cookies
        cms_cookies = {
            'cms': 'chfs1bavsllroemz2ub3t1pm',
            '_': '3ef27c5055b441e2b6024a583c33b127',
            'SideBarVisible': '1'
        }

        # LMS Cookies
        lms_cookies = {
            'PHPSESSID': '9a39sic1j1iurvtmfug5u3nqat'
        }

        for name, value in cms_cookies.items():
            self.session.cookies.set(name, value, domain='.bahria.edu.pk', path='/')

        for name, value in lms_cookies.items():
            self.session.cookies.set(name, value, domain='lms.bahria.edu.pk', path='/')

        print("✅ All cookies set successfully!")

    def check_course_assignments(self, course_code, course_name):
        try:
            form_data = {
                'courseName': course_code,
                'semesterName': 'MjAyNTM%3D'  # Fall-2025
            }

            print(f"📖 Checking {course_name}...")
            response = self.session.post(
                f"{self.base_lms_url}/Student/Assignments.php", 
                data=form_data,
                timeout=30
            )

            print(f"   HTTP Status: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table')

                if table:
                    assignments = []
                    rows = table.find_all('tr')[1:]  # Skip header row

                    for i, row in enumerate(rows):
                        cols = row.find_all('td')
                        if len(cols) >= 7:
                            assignment_number = cols[0].get_text(strip=True)
                            assignment_title = cols[1].get_text(strip=True)

                            # Skip empty rows
                            if not assignment_number and not assignment_title:
                                continue

                            assignment_data = {
                                'course_code': course_code,
                                'course_name': course_name,
                                'assignment_number': assignment_number or f"Row_{i+1}",
                                'assignment_title': assignment_title,
                                'assignment_file_available': "Assignment Not available" not in cols[2].get_text(),
                                'marks_available': "Not marked yet" not in cols[4].get_text(),
                                'marks_text': cols[4].get_text(strip=True),
                                'returned_submission_available': "---" not in cols[5].get_text(),
                                'deadline': cols[6].get_text(strip=True)
                            }
                            assignments.append(assignment_data)

                    print(f"   ✅ Found {len(assignments)} assignments")
                    return assignments
                else:
                    print(f"   ❌ No assignments table found")
                    return []
            else:
                print(f"   ❌ Failed to load page")
                return []

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []

    def detect_changes(self, assignments):
        changes = []

        for assignment in assignments:
            cursor = self.conn.cursor()
            cursor.execute(
                '''SELECT * FROM assignments 
                WHERE course_code = ? AND assignment_number = ? AND assignment_title = ?''',
                (assignment['course_code'], assignment['assignment_number'], assignment['assignment_title'])
            )

            if not cursor.fetchone():
                # New assignment found!
                changes.append(assignment)
                cursor.execute('''
                    INSERT INTO assignments 
                    (course_code, course_name, assignment_number, assignment_title,
                     assignment_file_available, marks_available, marks_text,
                     returned_submission_available, deadline)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    assignment['course_code'], assignment['course_name'],
                    assignment['assignment_number'], assignment['assignment_title'],
                    assignment['assignment_file_available'], assignment['marks_available'],
                    assignment['marks_text'], assignment['returned_submission_available'],
                    assignment['deadline']
                ))
                self.conn.commit()
                print(f"   🎉 NEW: {assignment['assignment_title']}")

        return changes

    def send_email(self, changes):
        try:
            # Your email configuration
            sender_email = "hellshot42@gmail.com"
            sender_password = "qyqi blbl zdrm ugyj"
            receiver_email = "hellshot42@gmail.com"

            for change in changes:
                subject = f"🚨 New Assignment - {change['course_name']}"

                message = f"""📚 BAHRIA LMS ALERT!

New Assignment Detected!

Course: {change['course_name']}
Assignment: {change['assignment_number']} - {change['assignment_title']}
Deadline: {change['deadline']}

Status:
- Assignment File: {'Available' if change['assignment_file_available'] else 'Not Available'}
- Marks: {change['marks_text']}
- Returned Submission: {'Available' if change['returned_submission_available'] else 'Not Available'}

Detected at: {datetime.now()}

Check your LMS: https://lms.bahria.edu.pk/Student/Assignments.php

---
Auto LMS Bot (Running on Render Cloud)
"""

                msg = MIMEText(message)
                msg['Subject'] = subject
                msg['From'] = sender_email
                msg['To'] = receiver_email

                # Send email
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)

                print(f"📧 Email sent for {change['course_name']}")

        except Exception as e:
            print(f"❌ Email error: {e}")

def run_bot():
    try:
        print("=" * 60)
        print(f"🕒 Checking LMS at {datetime.now()}")
        print("=" * 60)

        # Course list
        COURSES = {
            'MTM4OTA1': 'Applied Physics',
            'MTM4OTA2': 'Applied Physics Lab', 
            'MTM4OTA3': 'Computer Programming',
            'MTM4OTA4': 'Computer Programming Lab',
            'MTM4OTA5': 'Discrete Mathematics',
            'MTM4OTEw': 'ICT',
            'MTM4OTEx': 'ICT Lab',
            'MTM4OTEy': 'Islamic Studies',
            'MTM4OTEz': 'Professional Practices & Ethics',
            'MTM4OTE0': 'Tajweed'
        }

        # Initialize and run bot
        bot = ReplitLMSBot()
        bot.set_all_cookies()

        all_changes = []

        # Check each course
        for course_code, course_name in COURSES.items():
            print(f"🔍 Processing {course_name}...")
            assignments = bot.check_course_assignments(course_code, course_name)
            changes = bot.detect_changes(assignments)
            all_changes.extend(changes)
            print(f"✅ Completed {course_name}")
            time.sleep(2)  # Be nice to the server

        # Send notifications if changes found
        if all_changes:
            print(f"\n🎉 TOTAL: {len(all_changes)} new assignments found!")
            bot.send_email(all_changes)
            print("✅ Notifications sent!")
        else:
            print("\n✅ No new assignments found")

        bot.conn.close()
        print("🏁 Bot execution completed successfully!")
        
    except Exception as e:
        print(f"💥 FATAL ERROR in run_bot: {e}")
        raise  # Re-raise to be caught by background_bot


# Main loop for continuous operation
def background_bot():
    """Run bot in background thread with proper error handling"""
    # Initial delay to let Flask start completely
    time.sleep(10)
    
    while True:
        try:
            print(f"🔄 Starting bot cycle at {datetime.now()}")
            run_bot()
            print(f"✅ Bot cycle completed at {datetime.now()}")
            print(f"⏰ Next check in 30 minutes...")
            time.sleep(1800)  # 30 minutes
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in bot: {e}")
            print("🔄 Restarting bot in 2 minutes...")
            time.sleep(120)  # 2 minutes before retry

# Main loop for continuous operation
if __name__ == "__main__":
    print("🚀 Bahria LMS Bot - Render Edition")
    print("💡 This bot will run continuously and check every 30 minutes")
    print("🌐 Web server available on port 10000")
    
    # Start background bot thread
    bot_thread = threading.Thread(target=background_bot, daemon=True)
    bot_thread.start()
    print("✅ Background bot started!")
    
    # Start Flask app (this will block, which is fine for Render)
    print("🚀 Starting web server...")
    app.run(host='0.0.0.0', port=10000, debug=False)