import json
from unittest.mock import patch
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse
from django.core import mail
from django.core.files.base import ContentFile

from .models import User, Resume, Job, Application, Notification
from .notifications import notify_candidate

_TEST_SECRET = 'test-secret-token-for-unit-tests'
_NO_SECRET = override_settings(N8N_CALLBACK_SECRET=_TEST_SECRET, CALLBACK_SECRET=_TEST_SECRET)


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class UserModelTests(TestCase):
    def test_candidate_flags(self):
        u = User.objects.create_user(username='cand', password='pass', is_candidate=True)
        self.assertTrue(u.is_candidate)
        self.assertFalse(u.is_recruiter)
        self.assertFalse(u.has_resume())

    def test_recruiter_flags(self):
        u = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.assertTrue(u.is_recruiter)
        self.assertFalse(u.is_candidate)

    def test_company_field(self):
        u = User.objects.create_user(username='rec2', password='pass', is_recruiter=True, company='ACME')
        self.assertEqual(u.company, 'ACME')


class JobModelTests(TestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)

    def test_job_creation_defaults(self):
        job = Job.objects.create(
            title='Dev', company='Co', description='d',
            requirements='r', location='Luanda', created_by=self.recruiter,
        )
        self.assertEqual(str(job), 'Dev at Co')
        self.assertTrue(job.is_active)
        self.assertEqual(job.min_score_required, 0.0)

    def test_job_inactive(self):
        job = Job.objects.create(
            title='Dev', company='Co', description='d',
            requirements='r', location='Luanda', created_by=self.recruiter, is_active=False,
        )
        self.assertFalse(job.is_active)


class ApplicationModelTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='c@test.com')
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.job = Job.objects.create(title='Dev', company='Co', description='d', requirements='r', location='L', created_by=self.recruiter)

    def test_application_defaults(self):
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        self.assertEqual(app.status, 'pending')
        self.assertEqual(app.similarity_score, 0.0)
        self.assertEqual(app.get_status_display(), 'Pendente')

    def test_unique_together_constraint(self):
        from django.db import IntegrityError
        Application.objects.create(candidate=self.candidate, job=self.job)
        with self.assertRaises(IntegrityError):
            Application.objects.create(candidate=self.candidate, job=self.job)

    def test_status_choices(self):
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        for status, _ in Application.STATUS_CHOICES:
            app.status = status
            app.save()
            app.refresh_from_db()
            self.assertEqual(app.status, status)


# ---------------------------------------------------------------------------
# Controlo de acesso
# ---------------------------------------------------------------------------

class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True)
        self.recruiter = User.objects.create_user(
            username='rec', password='pass', is_recruiter=True, recruiter_approved=True
        )
        self.admin = User.objects.create_user(username='adm', password='pass', is_staff=True)

    def _login(self, username):
        user_map = {
            'cand': self.candidate,
            'rec': self.recruiter,
            'adm': self.admin,
        }
        self.client.force_login(user_map[username])

    def test_dashboard_redirects_anonymous(self):
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_candidate_cannot_access_dashboard(self):
        self._login('cand')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp, reverse('home'))

    def test_unapproved_recruiter_cannot_access_dashboard(self):
        unapproved = User.objects.create_user(
            username='rec_unap', password='pass', is_recruiter=True, recruiter_approved=False
        )
        self.client.force_login(unapproved)
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp, reverse('home'))

    def test_recruiter_accesses_dashboard(self):
        self._login('rec')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_accesses_dashboard(self):
        self._login('adm')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_kanban_requires_recruiter(self):
        self._login('cand')
        resp = self.client.get(reverse('dashboard_kanban'))
        self.assertRedirects(resp, reverse('home'))

    def test_analytics_requires_recruiter(self):
        self._login('cand')
        resp = self.client.get(reverse('analytics_dashboard'))
        self.assertRedirects(resp, reverse('home'))

    def test_job_manage_requires_recruiter(self):
        self._login('cand')
        resp = self.client.get(reverse('job_manage'))
        self.assertRedirects(resp, reverse('home'))

    def test_upload_requires_login(self):
        resp = self.client.get(reverse('upload_resume'))
        self.assertEqual(resp.status_code, 302)

    def test_profile_requires_login(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# Vagas
# ---------------------------------------------------------------------------

class JobViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='c@test.com')
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.job = Job.objects.create(
            title='Engenheiro', company='TechCo', description='Desenvolver sistemas.',
            requirements='Python, Django', location='Luanda',
            created_by=self.recruiter, contact_email_primary='hr@tech.co',
        )

    def test_job_list_visible(self):
        self.client.force_login(self.candidate)
        resp = self.client.get(reverse('job_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Engenheiro')

    def test_job_detail_visible(self):
        self.client.force_login(self.candidate)
        resp = self.client.get(reverse('job_detail', kwargs={'pk': self.job.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Engenheiro')
        self.assertContains(resp, 'Python, Django')

    def test_job_detail_inactive_returns_404(self):
        self.job.is_active = False
        self.job.save()
        self.client.force_login(self.candidate)
        resp = self.client.get(reverse('job_detail', kwargs={'pk': self.job.pk}))
        self.assertEqual(resp.status_code, 404)

    def test_apply_without_resume_redirects(self):
        self.client.force_login(self.candidate)
        resp = self.client.post(reverse('apply_job', kwargs={'pk': self.job.pk}))
        self.assertRedirects(resp, reverse('upload_resume'))

    def test_apply_with_resume_creates_application(self):
        Resume.objects.create(candidate=self.candidate, file=ContentFile(b'%PDF', name='cv.pdf'), parsed_text='Python')
        self.client.force_login(self.candidate)
        with patch('recruitment.views.send_application_for_scoring'):
            resp = self.client.post(reverse('apply_job', kwargs={'pk': self.job.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Application.objects.filter(candidate=self.candidate, job=self.job).count(), 1)

    def test_apply_twice_does_not_duplicate(self):
        Resume.objects.create(candidate=self.candidate, file=ContentFile(b'%PDF', name='cv.pdf'), parsed_text='Python')
        self.client.force_login(self.candidate)
        with patch('recruitment.views.send_application_for_scoring'):
            self.client.post(reverse('apply_job', kwargs={'pk': self.job.pk}))
            self.client.post(reverse('apply_job', kwargs={'pk': self.job.pk}))
        self.assertEqual(Application.objects.filter(candidate=self.candidate, job=self.job).count(), 1)

    def test_withdraw_then_reapply(self):
        Resume.objects.create(candidate=self.candidate, file=ContentFile(b'%PDF', name='cv.pdf'), parsed_text='Python')
        app = Application.objects.create(candidate=self.candidate, job=self.job, status='pending')
        self.client.force_login(self.candidate)
        self.client.post(reverse('withdraw_application', kwargs={'application_id': app.pk}))
        app.refresh_from_db()
        self.assertEqual(app.status, 'withdrawn')
        with patch('recruitment.views.send_application_for_scoring'):
            self.client.post(reverse('apply_job', kwargs={'pk': self.job.pk}))
        app.refresh_from_db()
        self.assertEqual(app.status, 'pending')


# ---------------------------------------------------------------------------
# Notificações e email
# ---------------------------------------------------------------------------

class NotificationTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='cand@test.com')
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.job = Job.objects.create(title='Dev', company='Co', description='d', requirements='r', location='L', created_by=self.recruiter)
        self.app = Application.objects.create(candidate=self.candidate, job=self.job)

    def test_pending_creates_no_notification(self):
        notify_candidate(self.app)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_pre_selected_creates_notification_and_email(self):
        self.app.status = 'pre_selected'
        notify_candidate(self.app)
        self.assertEqual(Notification.objects.filter(user=self.candidate).count(), 1)
        notification = Notification.objects.get(user=self.candidate)
        self.assertIn('pré-seleccionada', notification.message)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('cand@test.com', mail.outbox[0].to)
        self.assertIn('KUBUKA', mail.outbox[0].subject)

    def test_rejected_notification(self):
        self.app.status = 'rejected'
        notify_candidate(self.app)
        notification = Notification.objects.get(user=self.candidate)
        self.assertIn('não foi seleccionada', notification.message)
        self.assertEqual(len(mail.outbox), 1)

    def test_interview_scheduled_with_date(self):
        from django.utils import timezone
        import datetime
        self.app.status = 'interview_scheduled'
        self.app.interview_date = timezone.now() + datetime.timedelta(days=3)
        notify_candidate(self.app)
        notification = Notification.objects.get(user=self.candidate)
        self.assertIn('Entrevista', notification.message)
        self.assertIn('em ', notification.message)

    def test_no_email_without_candidate_email(self):
        self.candidate.email = ''
        self.candidate.save()
        self.app.status = 'pre_selected'
        notify_candidate(self.app)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Notification.objects.count(), 1)

    def test_notifications_view_shows_unread(self):
        Notification.objects.create(user=self.candidate, message='Teste', application=self.app)
        client = Client()
        client.force_login(self.candidate)
        resp = client.get(reverse('notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Teste')

    def test_mark_notification_read(self):
        notif = Notification.objects.create(user=self.candidate, message='Teste', application=self.app)
        self.assertFalse(notif.is_read)
        client = Client()
        client.force_login(self.candidate)
        client.post(reverse('mark_notification_read', kwargs={'pk': notif.pk}))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


# ---------------------------------------------------------------------------
# Auto-triagem
# ---------------------------------------------------------------------------

@_NO_SECRET
class AutoTriageTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='c@test.com')
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.job = Job.objects.create(
            title='Dev', company='Co', description='d', requirements='r', location='L',
            created_by=self.recruiter, contact_email_primary='hr@co.com',
            min_score_required=60.0,
        )
        self.app = Application.objects.create(candidate=self.candidate, job=self.job, awaiting_score=True)

    def _post_score(self, score):
        from .callback_views import application_score_result
        factory = RequestFactory()
        request = factory.post(
            f'/api/application/{self.app.pk}/score-result/',
            data=json.dumps({'similarity_score': score}),
            content_type='application/json',
            HTTP_X_KUBUKA_SECRET=_TEST_SECRET,
        )
        return application_score_result(request, self.app.pk)

    def test_score_below_threshold_auto_rejects(self):
        resp = self._post_score(40)
        self.assertEqual(resp.status_code, 200)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'rejected')
        self.assertIn('Triagem automática', self.app.match_feedback)
        self.assertEqual(len(mail.outbox), 1)

    def test_score_above_threshold_stays_pending(self):
        resp = self._post_score(75)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'pending')
        self.assertEqual(len(mail.outbox), 0)

    def test_score_equal_threshold_stays_pending(self):
        resp = self._post_score(60)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'pending')

    def test_no_min_score_never_auto_rejects(self):
        self.job.min_score_required = 0.0
        self.job.save()
        self._post_score(5)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'pending')


# ---------------------------------------------------------------------------
# Perfil — edição
# ---------------------------------------------------------------------------

class ProfileEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.recruiter = User.objects.create_user(
            username='rec', password='pass', is_recruiter=True, email='rec@test.com'
        )

    def test_profile_get(self):
        self.client.force_login(self.recruiter)
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'rec@test.com')

    def test_profile_edit_name_and_company(self):
        self.client.force_login(self.recruiter)
        resp = self.client.post(reverse('profile'), {
            'first_name': 'Manuel',
            'last_name': 'Zau',
            'email': 'newemail@test.com',
            'company': 'TechAngola',
        })
        self.assertRedirects(resp, reverse('profile'))
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.first_name, 'Manuel')
        self.assertEqual(self.recruiter.last_name, 'Zau')
        self.assertEqual(self.recruiter.email, 'newemail@test.com')
        self.assertEqual(self.recruiter.company, 'TechAngola')

    def test_profile_edit_candidate(self):
        candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='c@test.com')
        self.client.force_login(candidate)
        resp = self.client.post(reverse('profile'), {
            'first_name': 'Ana',
            'last_name': 'Silva',
            'email': 'ana@test.com',
            'company': '',
        })
        self.assertRedirects(resp, reverse('profile'))
        candidate.refresh_from_db()
        self.assertEqual(candidate.first_name, 'Ana')


# ---------------------------------------------------------------------------
# Callback — score result
# ---------------------------------------------------------------------------

@_NO_SECRET
class CallbackTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(username='cand', password='pass', is_candidate=True, email='c@test.com')
        self.recruiter = User.objects.create_user(username='rec', password='pass', is_recruiter=True)
        self.job = Job.objects.create(title='Dev', company='Co', description='d', requirements='r', location='L', created_by=self.recruiter)
        self.app = Application.objects.create(candidate=self.candidate, job=self.job, awaiting_score=True)

    def _post_score(self, score):
        from .callback_views import application_score_result
        factory = RequestFactory()
        req = factory.post(
            '/', data=json.dumps({'similarity_score': score}),
            content_type='application/json',
            HTTP_X_KUBUKA_SECRET=_TEST_SECRET,
        )
        return application_score_result(req, self.app.pk)

    def test_score_saved(self):
        self._post_score(72)
        self.app.refresh_from_db()
        self.assertEqual(self.app.similarity_score, 72.0)

    def test_invalid_json_returns_400(self):
        from .callback_views import application_score_result
        factory = RequestFactory()
        req = factory.post(
            '/', data='not json', content_type='application/json',
            HTTP_X_KUBUKA_SECRET=_TEST_SECRET,
        )
        resp = application_score_result(req, self.app.pk)
        self.assertEqual(resp.status_code, 400)

    def test_missing_score_field_returns_400(self):
        from .callback_views import application_score_result
        factory = RequestFactory()
        req = factory.post(
            '/', data=json.dumps({'other': 'value'}),
            content_type='application/json',
            HTTP_X_KUBUKA_SECRET=_TEST_SECRET,
        )
        resp = application_score_result(req, self.app.pk)
        self.assertEqual(resp.status_code, 400)

    def test_score_clamped_to_100(self):
        self._post_score(150)
        self.app.refresh_from_db()
        self.assertEqual(self.app.similarity_score, 100.0)

    def test_score_clamped_to_0(self):
        self._post_score(-50)
        self.app.refresh_from_db()
        self.assertEqual(self.app.similarity_score, 0.0)
