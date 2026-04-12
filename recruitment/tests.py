from django.test import TestCase, Client
from django.urls import reverse
from .models import User, Resume
from django.core.files.uploadedfile import SimpleUploadedFile

class RecruitmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testcandidate', password='password123', is_candidate=True)
        self.admin = User.objects.create_superuser(username='testadmin', password='password123', email='admin@test.com', is_admin=True)

    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RecrutaIA")

    def test_resume_upload_requires_login(self):
        response = self.client.get(reverse('upload_resume'))
        self.assertEqual(response.status_code, 302)

    def test_resume_upload(self):
        self.client.login(username='testcandidate', password='password123')
        # Creating a minimal valid-ish PDF structure for PyPDF2 to not crash if possible,
        # but even if it fails, our code handles it.
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 51 >>\nstream\nBT /F1 12 Tf 70 700 Td (Hello World) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000062 00000 n \n0000000125 00000 n \n0000000219 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n320\n%%EOF"
        pdf_file = SimpleUploadedFile("resume.pdf", pdf_content, content_type="application/pdf")

        response = self.client.post(reverse('upload_resume'), {'file': pdf_file})
        self.assertEqual(response.status_code, 302) # Redirects to success

        resume = Resume.objects.get(candidate=self.user)
        self.assertIsNotNone(resume.score)
        self.assertTrue(resume.score >= 50)

    def test_admin_dashboard_access(self):
        # Candidate cannot access
        self.client.login(username='testcandidate', password='password123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Admin can access
        self.client.login(username='testadmin', password='password123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_api_resume_list(self):
        self.client.login(username='testadmin', password='password123')
        response = self.client.get(reverse('resume-api-list'))
        self.assertEqual(response.status_code, 200)

    def test_profile_view(self):
        self.client.login(username='testcandidate', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testcandidate")
