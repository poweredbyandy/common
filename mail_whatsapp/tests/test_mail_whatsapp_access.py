from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMailWhatsappAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.own_user = new_test_user(
            cls.env,
            login="wa_own",
            name="Own Agent",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_own",
        )
        cls.other_own_user = new_test_user(
            cls.env,
            login="wa_own_other",
            name="Other Own Agent",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_own",
        )
        cls.all_user = new_test_user(
            cls.env,
            login="wa_all",
            name="All Chats Agent",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_user",
        )
        cls.manager = new_test_user(
            cls.env,
            login="wa_manager",
            name="Account Manager",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_account_manager",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="wa_outsider",
            name="Other Account Agent",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_user",
        )
        cls.no_whatsapp = new_test_user(
            cls.env, login="wa_none", name="No WhatsApp", groups="base.group_user"
        )
        cls.account = cls._create_account("Sales Line", "access_sales_phone")
        cls.account.write(
            {
                "agent_user_ids": [
                    Command.set(
                        (cls.own_user | cls.other_own_user | cls.all_user).ids
                    )
                ],
                "manager_user_ids": [Command.set(cls.manager.ids)],
                "notify_user_ids": [Command.set(cls.manager.ids)],
            }
        )
        cls.other_account = cls._create_account("Support Line", "access_support_phone")
        cls.other_account.write(
            {
                "agent_user_ids": [Command.set(cls.outsider.ids)],
                "notify_user_ids": [Command.set(cls.outsider.ids)],
            }
        )
        Channel = cls.env["discuss.channel"]
        cls.free_chat = Channel._get_whatsapp_channel(
            "+584125550301", cls.account, "Free", create_if_not_found=True
        )
        cls.own_chat = Channel._get_whatsapp_channel(
            "+584125550302", cls.account, "Mine", create_if_not_found=True
        )
        cls.other_chat = Channel._get_whatsapp_channel(
            "+584125550303", cls.account, "Theirs", create_if_not_found=True
        )
        cls.foreign_chat = Channel._get_whatsapp_channel(
            "+584125550304", cls.other_account, "Foreign", create_if_not_found=True
        )
        cls.own_chat.whatsapp_user_id = cls.own_user
        cls.other_chat.whatsapp_user_id = cls.other_own_user

    @classmethod
    def _create_account(cls, name, phone_uid):
        return cls.env["mail.whatsapp.account"].create(
            {
                "name": name,
                "setup_mode": "manual",
                "app_uid": "app_%s" % phone_uid,
                "app_secret": "secret",
                "account_uid": "waba_%s" % phone_uid,
                "phone_uid": phone_uid,
                "display_phone_number": "+10000000001",
                "token": "token",
                "notify_user_ids": [Command.set(cls.env.ref("base.user_admin").ids)],
            }
        )

    def _visible_chats(self, user):
        chats = self.free_chat | self.own_chat | self.other_chat | self.foreign_chat
        return self.env["discuss.channel"].with_user(user).search(
            [("id", "in", chats.ids)]
        )

    def test_own_chats_level(self):
        self.assertEqual(
            self._visible_chats(self.own_user), self.free_chat | self.own_chat
        )
        with self.assertRaises(AccessError):
            self.other_chat.with_user(self.own_user).read(["name"])

    def test_all_chats_level(self):
        self.assertEqual(
            self._visible_chats(self.all_user),
            self.free_chat | self.own_chat | self.other_chat,
        )
        self.assertEqual(self._visible_chats(self.outsider), self.foreign_chat)

    def test_admin_and_users_without_whatsapp(self):
        admin = self.env.ref("base.user_admin")
        self.assertEqual(len(self._visible_chats(admin)), 4)
        self.assertFalse(self._visible_chats(self.no_whatsapp))

    def test_accounts_by_team(self):
        Account = self.env["mail.whatsapp.account"]
        accounts = self.account | self.other_account
        visible = Account.with_user(self.own_user).search([("id", "in", accounts.ids)])
        self.assertEqual(visible, self.account)
        self.account.with_user(self.manager).write({"name": "Sales Line 2"})
        self.assertEqual(self.account.name, "Sales Line 2")
        with self.assertRaises(AccessError):
            self.account.with_user(self.all_user).write({"name": "Nope"})
        with self.assertRaises(AccessError):
            self.account.with_user(self.manager).write(
                {"manager_user_ids": [Command.link(self.all_user.id)]}
            )

    def test_take_and_release_chat(self):
        free = self.free_chat.with_user(self.own_user)
        free.whatsapp_set_responsible(self.own_user.id)
        self.assertEqual(self.free_chat.whatsapp_user_id, self.own_user)
        self.assertIn(self.own_user.partner_id, self.free_chat.channel_member_ids.partner_id)
        self.assertFalse(self._visible_chats(self.other_own_user) & self.free_chat)
        with self.assertRaises(AccessError):
            self.free_chat.with_user(self.other_own_user).whatsapp_set_responsible(
                self.other_own_user.id
            )
        free.whatsapp_set_responsible(False)
        self.assertFalse(self.free_chat.whatsapp_user_id)

    def test_manager_reassigns_and_members_follow(self):
        self.own_chat.add_members(partner_ids=self.own_user.partner_id.ids)
        users = self.own_chat.with_user(self.manager).whatsapp_get_assignable_users()
        self.assertIn(self.other_own_user.id, [user["id"] for user in users])
        self.own_chat.with_user(self.manager).whatsapp_set_responsible(
            self.other_own_user.id
        )
        members = self.own_chat.channel_member_ids.partner_id
        self.assertIn(self.other_own_user.partner_id, members)
        self.assertNotIn(self.own_user.partner_id, members)
        with self.assertRaises(AccessError):
            self.own_chat.with_user(self.own_user).read(["name"])

    def test_bulk_assign_wizard(self):
        chats = (self.free_chat | self.other_chat).with_user(self.manager)
        action = chats.action_whatsapp_assign()
        wizard = self.env["mail.whatsapp.assign"].with_user(self.manager).browse(
            action["res_id"]
        )
        self.assertIn(self.own_user, wizard.allowed_user_ids)
        self.assertNotIn(self.outsider, wizard.allowed_user_ids)
        wizard.user_id = self.own_user
        wizard.action_assign()
        self.assertEqual(self.free_chat.whatsapp_user_id, self.own_user)
        self.assertEqual(self.other_chat.whatsapp_user_id, self.own_user)
        self.assertEqual(
            self._visible_chats(self.own_user),
            self.free_chat | self.own_chat | self.other_chat,
        )

    def test_bulk_assign_wizard_respects_levels(self):
        action = self.free_chat.with_user(self.own_user).action_whatsapp_assign()
        wizard = self.env["mail.whatsapp.assign"].with_user(self.own_user).browse(
            action["res_id"]
        )
        self.assertEqual(wizard.allowed_user_ids, self.own_user)
        wizard.user_id = self.other_own_user
        with self.assertRaises(UserError):
            wizard.action_assign()
        with self.assertRaises(AccessError):
            self.other_chat.with_user(self.own_user).action_whatsapp_assign()
        mixed = (self.free_chat | self.foreign_chat).with_user(
            self.env.ref("base.user_admin")
        )
        wizard = self.env["mail.whatsapp.assign"].browse(
            mixed.action_whatsapp_assign()["res_id"]
        )
        self.assertFalse(
            (self.own_user | self.outsider) & wizard.allowed_user_ids
        )

    def test_advisor_round_robin(self):
        candidates = self.free_chat._whatsapp_assignable_users().sorted("id")
        self.assertGreater(len(candidates), 1)
        self.account.advisor_last_user_id = False
        self.assertEqual(self.free_chat._whatsapp_next_advisor(), candidates[0])
        self.assertEqual(self.free_chat._whatsapp_next_advisor(), candidates[1])
        self.account.advisor_last_user_id = candidates[-1]
        self.assertEqual(self.free_chat._whatsapp_next_advisor(), candidates[0])

    def test_request_advisor_without_mobile_still_assigns(self):
        self.account.advisor_last_user_id = False
        advisor = self.free_chat._whatsapp_assignable_users().sorted("id")[0]
        advisor.partner_id.write({"mobile": False, "phone": False})
        self.assertEqual(self.free_chat._whatsapp_request_advisor("Pide humano"), advisor)
        self.assertEqual(self.free_chat.whatsapp_user_id, advisor)
        note = self.free_chat.message_ids[:1]
        self.assertEqual(note.message_type, "notification")
        self.assertIn("no valid mobile number", note.body)
        self.assertIn("Pide humano", note.body)
        self.assertEqual(self.own_chat._whatsapp_request_advisor(), self.own_user)

    def test_first_reply_assigns_chat(self):
        with patch.object(
            type(self.env["mail.whatsapp.message"]), "_send_message", lambda self: True
        ):
            self.free_chat.with_user(self.all_user).message_post(
                body="Hola",
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
            )
            self.assertEqual(self.free_chat.whatsapp_user_id, self.all_user)
            self.free_chat.with_user(self.manager).message_post(
                body="Sigo yo",
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
            )
        self.assertEqual(self.free_chat.whatsapp_user_id, self.all_user)

    def test_focus_search_without_membership(self):
        result = self.env["discuss.channel"].with_user(self.all_user).whatsapp_focus_search(
            "", include_messages=False
        )
        chats = self.free_chat | self.own_chat | self.other_chat
        self.assertEqual(set(result["channel_ids"]) & set((chats | self.foreign_chat).ids), set(chats.ids))
        mine = self.env["discuss.channel"].with_user(self.own_user).whatsapp_focus_search(
            "", include_messages=False, responsible="me"
        )
        self.assertEqual(
            set(mine["channel_ids"]) & set((chats | self.foreign_chat).ids),
            {self.own_chat.id},
        )

    def test_whatsapp_messages_follow_chat_access(self):
        mail_message = self.other_chat.message_post(
            body="Privado",
            message_type="comment",
            author_id=self.other_chat.whatsapp_partner_id.id,
            whatsapp_inbound_msg_uid="wamid.ACCESS_TEST",
        )
        wa_message = self.env["mail.whatsapp.message"].search(
            [("mail_message_id", "=", mail_message.id)]
        )
        self.assertTrue(wa_message)
        Message = self.env["mail.whatsapp.message"]
        self.assertFalse(
            Message.with_user(self.own_user).search([("id", "=", wa_message.id)])
        )
        self.assertTrue(
            Message.with_user(self.all_user).search([("id", "=", wa_message.id)])
        )

    def test_whatsapp_account_can_be_created_with_only_a_name(self):
        admin = new_test_user(
            self.env,
            login="wa_admin_create",
            name="WA Admin Create",
            groups="base.group_user,mail_whatsapp.group_mail_whatsapp_admin",
        )
        Account = self.env["mail.whatsapp.account"].with_user(admin)
        account = Account.create({"name": "Draft Line"})
        self.assertEqual(account.name, "Draft Line")
        self.assertIn(admin, account.notify_user_ids)
        self.assertFalse(account.phone_uid)
        self.assertFalse(account.account_uid)
        with self.assertRaises(ValidationError):
            account.write({"phone_uid": "123"})
        account.write(
            {
                "account_uid": "waba",
                "phone_uid": "phone",
                "token": "token-value",
            }
        )
        self.assertEqual(account.phone_uid, "phone")
        account.unlink()

    def test_whatsapp_chat_shows_the_contact_company(self):
        company = self.env["res.partner"].create(
            {"name": "Acme C.A.", "is_company": True, "vat": "J123"}
        )
        contact = self.own_chat.whatsapp_partner_id
        self.assertFalse(self.own_chat.whatsapp_company_id)
        contact.write({"parent_id": company.id})
        self.assertEqual(self.own_chat.whatsapp_company_id, company)
        store = self.own_chat._whatsapp_company_store_data()
        self.assertEqual(store["whatsappCompanyId"], company.id)
        self.assertEqual(store["whatsappCompanyName"], company.display_name)
        found = self.env["discuss.channel"].with_user(self.all_user).whatsapp_focus_search(
            "Acme", include_messages=False
        )
        self.assertIn(self.own_chat.id, found["channel_ids"])
