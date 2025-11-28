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

@app.route('/force-check')
def force_check():
    """Manually trigger the bot to run right now"""
    import threading
    
    def run_manual_check():
        print("🔄 MANUAL CHECK TRIGGERED VIA WEB!")
        run_bot()
    
    thread = threading.Thread(target=run_manual_check, daemon=True)
    thread.start()
    
    return "🔄 Manual check triggered! Check logs in 2 minutes."

@app.route('/debug-html')
def debug_html():
    """Check the actual HTML structure of one course"""
    try:
        bot = ReplitLMSBot()
        bot.set_all_cookies()
        
        # Test with one course
        course_code = 'MTM4OTA1'  # Applied Physics
        form_data = {
            'courseName': course_code,
            'semesterName': 'MjAyNTM%3D'
        }
        
        response = bot.session.post(
            "https://lms.bahria.edu.pk/Student/Assignments.php", 
            data=form_data,
            timeout=30
        )
        
        if response.status_code == 200:
            # Return the raw HTML for inspection
            return f"<pre>{response.text}</pre>"
        else:
            return f"Failed to load: HTTP {response.status_code}"
            
    except Exception as e:
        return f"Error: {e}"

@app.route('/check-auth')
def check_auth():
    """Check authentication status"""
    try:
        bot = ReplitLMSBot()
        
        # Test direct access to LMS
        response = bot.session.get(
            "https://lms.bahria.edu.pk/Student/Assignments.php",
            allow_redirects=False,
            timeout=10
        )
        
        result = f"""
        <h1>Authentication Check</h1>
        <p>Status Code: {response.status_code}</p>
        <p>Headers: {dict(response.headers)}</p>
        """
        
        if response.status_code in [301, 302]:
            redirect_to = response.headers.get('Location', 'Unknown')
            result += f"<p style='color: red;'>🚨 REDIRECTED TO: {redirect_to}</p>"
        elif response.status_code == 200:
            result += "<p style='color: green;'>✅ Successfully accessed LMS</p>"
            
        return result
        
    except Exception as e:
        return f"Error: {e}"
    
@app.route('/test-cookie')
def test_cookie():
    """Test if the manual cookie still works"""
    try:
        bot = ReplitLMSBot()
        
        # Use the simple manual cookie approach
        bot.session.cookies.clear()
        bot.session.cookies.set('PHPSESSID', '9a39sic1j1iurvtmfug5u3nqat', domain='lms.bahria.edu.pk', path='/')
        
        response = bot.session.get(
            "https://lms.bahria.edu.pk/Student/Assignments.php?s=MjAyNTM%3D&oc=MTM4OTA1",
            allow_redirects=False,
            timeout=10
        )
        
        result = f"""
        <h1>Cookie Test</h1>
        <p>Status: {response.status_code}</p>
        <p>Redirect: {response.headers.get('Location', 'No redirect')}</p>
        """
        
        if response.status_code == 200:
            result += "<p style='color: green;'>✅ Manual cookie STILL WORKS!</p>"
        else:
            result += "<p style='color: red;'>❌ Manual cookie FAILED!</p>"
            
        return result
        
    except Exception as e:
        return f"Error: {e}"    

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
     print("🔄 Setting up LMS session with manual cookie...")
    
    # Clear all cookies first
     self.session.cookies.clear()
    
     try:
        # ALWAYS use the working manual PHPSESSID (skip CMS login)
        print("   🔑 Setting manual PHPSESSID...")
        manual_cookies = {
            'PHPSESSID': '9a39sic1j1iurvtmfug5u3nqat'
        }
        
        for name, value in manual_cookies.items():
            self.session.cookies.set(name, value, domain='lms.bahria.edu.pk', path='/')
        
        # Test if cookies work
        print("   🧪 Testing cookies...")
        test_response = self.session.get(
            "https://lms.bahria.edu.pk/Student/Assignments.php",
            allow_redirects=False,
            timeout=10
        )
        
        print(f"   🧪 Cookie test: {test_response.status_code}")
        
        if test_response.status_code == 200:
            print("   ✅ Manual cookies WORKING!")
            if "Assignments" in test_response.text:
                print("   🎯 Successfully accessed Assignments page!")
            else:
                print("   ⚠️ On LMS but not assignments page")
        else:
            print(f"   ❌ Manual cookies failed: {test_response.status_code}")
            if test_response.status_code in [301, 302]:
                redirect_to = test_response.headers.get('Location', '')
                print(f"   🔀 Redirected to: {redirect_to}")
                
        # Print cookies for debugging
        print("   🍪 Current cookies:")
        for cookie in self.session.cookies:
            print(f"      {cookie.name}: {cookie.value} (domain: {cookie.domain})")
                
     except Exception as e:
        print(f"   ❌ Session setup failed: {e}")
        import traceback
        traceback.print_exc()

    def check_course_assignments(self, course_code, course_name):
     try:
        print(f"📖 Checking {course_name}...")
        
        url = f"{self.base_lms_url}/Student/Assignments.php?s=MjAyNTM%3D&oc={course_code}"
        
        print(f"   🔗 Using URL: {url}")
        
        response = self.session.get(
            url,
            timeout=30,
            headers={
                'Referer': f'{self.base_lms_url}/Student/Assignments.php'
            },
            allow_redirects=False  # Don't follow redirects automatically
        )

        print(f"   📡 GET Status: {response.status_code}")
        
        # Check if we got redirected to CMS
        if response.status_code in [301, 302]:
            redirect_location = response.headers.get('Location', '')
            print(f"   🔀 REDIRECTED to: {redirect_location}")
            if 'cms.bahria.edu.pk' in redirect_location:
                print("   🚨 Redirected to CMS - authentication issue!")
            return []
        
        # If we got a successful response, parse it
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            page_title = soup.find('title')
            
            if page_title:
                title_text = page_title.get_text(strip=True)
                print(f"   📄 Page title: {title_text}")
                
                # Check if we're on CMS instead of LMS
                if "CMS" in title_text:
                    print("   🚨 On CMS page instead of LMS - authentication failed!")
                    return []

            # Rest of your existing parsing logic...
            table = soup.find('table', {'class': 'table'})
            
            if table:
                # ... your existing assignment parsing code
                assignments = []
                rows = table.find_all('tr')[1:]  # Skip header row

                for i, row in enumerate(rows):
                    cols = row.find_all('td')
                    
                    # Check if this is the "no assignments" message row
                    if len(cols) == 1:
                        message = cols[0].get_text(strip=True)
                        if "please select a course" in message.lower() or "no assignments" in message.lower():
                            print(f"   ℹ️ No assignments available for {course_name}")
                            return []
                    
                    if len(cols) >= 7:
                        assignment_number = cols[0].get_text(strip=True)
                        assignment_title = cols[1].get_text(strip=True)

                        if not assignment_number or not assignment_title:
                            continue
                        if "please select" in assignment_title.lower():
                            continue
                        if "select a course" in assignment_title.lower():
                            continue

                        print(f"   🔍 Found assignment: {assignment_number} - {assignment_title}")
                        
                        assignment_data = {
                            'course_code': course_code,
                            'course_name': course_name,
                            'assignment_number': assignment_number,
                            'assignment_title': assignment_title,
                            'assignment_file_available': "Assignment Not available" not in cols[2].get_text(),
                            'marks_available': "Not marked yet" not in cols[4].get_text(),
                            'marks_text': cols[4].get_text(strip=True),
                            'returned_submission_available': "---" not in cols[5].get_text(),
                            'deadline': cols[6].get_text(strip=True)
                        }
                        assignments.append(assignment_data)

                print(f"   ✅ Found {len(assignments)} assignments for {course_name}")
                return assignments
            else:
                print(f"   ❌ No assignments table found")
                return []
        else:
            print(f"   ❌ Request failed with status: {response.status_code}")
            return []

     except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    def debug_course_page(self, course_code, course_name):
        """Debug method to see actual page content"""
        try:
            form_data = {
                'courseName': course_code,
                'semesterName': 'MjAyNTM%3D'
            }

            print(f"🐛 DEBUGGING {course_name}...")
            
            response = self.session.post(
                f"{self.base_lms_url}/Student/Assignments.php", 
                data=form_data,
                timeout=30
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Save the actual HTML to a file for inspection
                filename = f"debug_{course_name}.html"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"   💾 Saved HTML to: {filename}")
                
                # Look for ANY tables on the page
                tables = soup.find_all('table')
                print(f"   🔍 Found {len(tables)} total tables on page")
                
                for i, table in enumerate(tables):
                    print(f"   📊 Table {i+1}:")
                    print(f"      Classes: {table.get('class', 'No classes')}")
                    print(f"      ID: {table.get('id', 'No ID')}")
                    
                    # Count rows in this table
                    rows = table.find_all('tr')
                    print(f"      Rows: {len(rows)}")
                    
                    if len(rows) > 0:
                        # Show first row content
                        first_row = rows[0]
                        cols = first_row.find_all(['td', 'th'])
                        print(f"      Columns in first row: {len(cols)}")
                        for j, col in enumerate(cols):
                            print(f"        Col {j}: '{col.get_text(strip=True)}'")
                
                # Also check for any assignment-related text
                if "assignment" in response.text.lower():
                    print("   📋 Found 'assignment' text on page")
                if "no assignment" in response.text.lower():
                    print("   ❌ Found 'no assignment' text on page")
                if "not available" in response.text.lower():
                    print("   ⚠️ Found 'not available' text on page")
                    
            return True
            
        except Exception as e:
            print(f"   ❌ Debug failed: {e}")
            return False
        
    def test_post_request(self, course_code, course_name):
     """Test if URL parameters work"""
     print(f"🧪 TESTING URL PARAMS for {course_name}...")
    
    # Use URL parameters instead of POST
     url = f"{self.base_lms_url}/Student/Assignments.php?s=MjAyNTM%3D&oc={course_code}"
    
     response = self.session.get(url, timeout=30)
    
    # Save the response to see what we're actually getting
     filename = f"test_url_{course_name}.html"
     with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)
     print(f"   💾 Saved URL response to: {filename}")
    
    # Check if the course name appears in the dropdown as selected
     soup = BeautifulSoup(response.content, 'html.parser')
     select_element = soup.find('select', {'id': 'courseId'})
     if select_element:
        selected_option = select_element.find('option', selected=True)
        if selected_option:
            selected_text = selected_option.get_text(strip=True)
            print(f"   🔍 Selected course in dropdown: {selected_text}")
            
            # Also check the table for actual assignments
            table = soup.find('table', {'class': 'table'})
            if table:
                rows = table.find_all('tr')
                print(f"   📊 Table rows found: {len(rows)}")
                
                # Look for assignment rows (skip header and message rows)
                assignment_rows = []
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 7:  # Actual assignment row
                        assignment_rows.append(row)
                
                print(f"   📋 Actual assignment rows: {len(assignment_rows)}")
                
                if assignment_rows:
                    for i, row in enumerate(assignment_rows[:2]):  # Show first 2
                        cols = row.find_all('td')
                        print(f"     Assignment {i+1}: {cols[0].get_text(strip=True)} - {cols[1].get_text(strip=True)}")
        else:
            print("   ⚠️ No course selected in dropdown")
    
     return response.status_code == 200 

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

def background_bot():
    """Run bot in background thread with proper error handling"""
    print("🎯 Background bot thread STARTED!")
    # Initial delay to let Flask start completely
    print("⏳ Waiting 10 seconds for Flask to stabilize...")
    time.sleep(10)
    
    check_count = 0
    while True:
        try:
            check_count += 1
            print(f"🔄 [{check_count}] Starting bot cycle at {datetime.now()}")
            run_bot()
            print(f"✅ [{check_count}] Bot cycle completed at {datetime.now()}")
            print(f"⏰ Next check in 30 minutes...")
            time.sleep(1800)  # 30 minutes
            
        except Exception as e:
            print(f"❌ [{check_count}] CRITICAL ERROR in bot: {e}")
            import traceback
            traceback.print_exc()  # This will show the full error stack
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