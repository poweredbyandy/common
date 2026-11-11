from unittest.mock import patch

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestActivityAssignmentNotification(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._send_patch = patch(
            "odoo.addons.mail_gmail_user.models.mail_mail.MailMail.send",
            autospec=True,
            return_value=True,
        )
        cls._send_patch.start()
        cls.addClassCleanup(cls._send_patch.stop)
        cls.assignee = new_test_user(
            cls.env,
            login="activity_assignee",
            groups="base.group_user,sales_team.group_sale_salesman,mail.group_mail_notification_type_inbox",
        )
        cls.email_assignee = new_test_user(
            cls.env,
            login="activity_assignee_email",
            groups="base.group_user",
        )
        cls.document = cls.env["res.partner"].create({"name": "Cliente de la actividad"})
        cls.activity_type = cls.env.ref("mail.mail_activity_data_todo")

    def _create_activity(self, user, summary="Llamar al cliente"):
        return self.env["mail.activity"].create({
            "activity_type_id": self.activity_type.id,
            "res_model_id": self.env["ir.model"]._get_id("res.partner"),
            "res_id": self.document.id,
            "user_id": user.id,
            "summary": summary,
        })

    def _inbox_bodies(self, user):
        notifications = self.env["mail.notification"].sudo().search([
            ("res_partner_id", "=", user.partner_id.id),
            ("notification_type", "=", "inbox"),
            ("mail_message_id.model", "=", "res.partner"),
            ("mail_message_id.res_id", "=", self.document.id),
        ])
        return notifications.mail_message_id.mapped("body")

    def test_other_user_gets_inbox_with_open_link(self):
        self._create_activity(self.assignee)
        bodies = self._inbox_bodies(self.assignee)
        self.assertTrue(bodies)
        body = " ".join(bodies)
        self.assertIn("Se te asignó:", body)
        self.assertIn("Llamar al cliente", body)
        self.assertIn("Cliente de la actividad", body)
        self.assertIn("/web#id=%s" % self.document.id, body)
        self.assertIn("model=res.partner", body)
        self.assertIn("Abrir", body)

    def test_self_assignment_gets_inbox(self):
        document = self.env["res.partner"].with_user(self.assignee).create({
            "name": "Documento propio",
        })
        self.env["mail.activity"].with_user(self.assignee).create({
            "activity_type_id": self.activity_type.id,
            "res_model_id": self.env["ir.model"]._get_id("res.partner"),
            "res_id": document.id,
            "user_id": self.assignee.id,
            "summary": "Revisar expediente",
        })
        self.document = document
        bodies = self._inbox_bodies(self.assignee)
        self.assertTrue(bodies)
        body = " ".join(bodies)
        self.assertIn("Revisar expediente", body)
        self.assertIn("Abrir", body)

    def test_reassignment_notifies_new_user(self):
        activity = self._create_activity(self.assignee, summary="Primera")
        activity.write({"user_id": self.email_assignee.id, "summary": "Reasignada"})
        bodies = self._inbox_bodies(self.email_assignee)
        self.assertTrue(any("Reasignada" in body or "Se te asignó:" in body for body in bodies))
        self.assertTrue(any("Abrir" in body for body in bodies))

    def test_email_preference_still_gets_inbox(self):
        self._create_activity(self.email_assignee, summary="Por correo")
        bodies = self._inbox_bodies(self.email_assignee)
        self.assertTrue(bodies)
        self.assertIn("Abrir", " ".join(bodies))
        self.assertIn("/web#id=%s" % self.document.id, " ".join(bodies))
