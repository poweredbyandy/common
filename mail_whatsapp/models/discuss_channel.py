import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import SQL

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail_whatsapp.tools import phone_validation as wa_phone_validation

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    channel_type = fields.Selection(
        selection_add=[("whatsapp", "WhatsApp Conversation")],
        ondelete={"whatsapp": "cascade"},
    )
    whatsapp_number = fields.Char(string="Phone Number")
    whatsapp_channel_valid_until = fields.Datetime(
        string="WhatsApp Channel Valid Until",
        compute="_compute_whatsapp_channel_valid_until",
    )
    last_wa_mail_message_id = fields.Many2one(
        "mail.message",
        string="Last WA Partner Mail Message",
        index="btree_not_null",
    )
    whatsapp_partner_id = fields.Many2one(
        "res.partner",
        string="WhatsApp Partner",
        index="btree_not_null",
    )
    whatsapp_company_id = fields.Many2one(
        "res.partner",
        string="Company",
        compute="_compute_whatsapp_company_id",
        store=True,
        index="btree_not_null",
        help="Company of the WhatsApp contact when that person belongs to one.",
    )
    whatsapp_last_replier_partner_id = fields.Many2one(
        "res.partner",
        string="Last Replier",
        index="btree_not_null",
        help="Last Odoo user who replied in this WhatsApp conversation.",
    )
    whatsapp_tag_ids = fields.Many2many(
        "mail.whatsapp.tag",
        "mail_whatsapp_channel_tag_rel",
        "channel_id",
        "tag_id",
        string="WhatsApp Tags",
    )
    wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="WhatsApp Business Account",
    )
    whatsapp_channel_active = fields.Boolean(
        string="Is WhatsApp Channel Active",
        compute="_compute_whatsapp_channel_active",
    )
    whatsapp_user_id = fields.Many2one(
        "res.users",
        string="WhatsApp Responsible",
        index="btree_not_null",
        help="Agent in charge of this WhatsApp chat. Users with the Own Chats "
        "level see their chats and the unassigned ones.",
    )
    whatsapp_access_ok = fields.Boolean(
        compute="_compute_whatsapp_access_ok",
        search="_search_whatsapp_access_ok",
    )

    _sql_constraints = [
        (
            "group_public_id_check",
            "CHECK (channel_type = 'channel' OR channel_type = 'whatsapp' "
            "OR group_public_id IS NULL)",
            "Group authorization and group auto-subscription are only "
            "supported on channels and whatsapp.",
        ),
    ]

    @api.constrains("channel_type", "whatsapp_number")
    def _check_whatsapp_number(self):
        missing_number = self.filtered(
            lambda channel: channel.channel_type == "whatsapp"
            and not channel.whatsapp_number
        )
        if missing_number:
            raise ValidationError(
                _(
                    "A phone number is required for WhatsApp channels %(channel_names)s",
                    channel_names=", ".join(missing_number.mapped("display_name")),
                )
            )

    @api.constrains("group_public_id", "group_ids")
    def _constraint_group_id_channel(self):
        valid_channels = self.filtered(
            lambda channel: channel.channel_type == "whatsapp"
        )
        return super(
            DiscussChannel, self - valid_channels
        )._constraint_group_id_channel()

    @api.depends("last_wa_mail_message_id", "last_wa_mail_message_id.create_date")
    def _compute_whatsapp_channel_valid_until(self):
        for channel in self:
            channel.whatsapp_channel_valid_until = (
                channel.last_wa_mail_message_id.create_date + timedelta(hours=24)
                if channel.channel_type == "whatsapp"
                and channel.last_wa_mail_message_id
                else False
            )

    @api.depends("whatsapp_channel_valid_until")
    def _compute_whatsapp_channel_active(self):
        for channel in self:
            channel.whatsapp_channel_active = bool(
                channel.whatsapp_channel_valid_until
                and channel.whatsapp_channel_valid_until > fields.Datetime.now()
            )

    @api.model
    def _whatsapp_sees_everything(self, user):
        return (
            user._is_superuser()
            or user.has_group("mail_whatsapp.group_mail_whatsapp_admin")
            or user.has_group("base.group_system")
        )

    @api.model
    def _whatsapp_user_accounts(self, user):
        if not user.has_group("mail_whatsapp.group_mail_whatsapp_own"):
            return self.env["mail.whatsapp.account"]
        return (
            self.env["mail.whatsapp.account"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("agent_user_ids", "in", user.id),
                    ("manager_user_ids", "in", user.id),
                ]
            )
        )

    @api.model
    def _whatsapp_access_domain(self, user=None, prefix=""):
        """Domain of the WhatsApp chats ``user`` may see by access level."""
        user = user or self.env.user
        if self._whatsapp_sees_everything(user):
            return expression.TRUE_DOMAIN
        accounts = self._whatsapp_user_accounts(user)
        if not accounts:
            return expression.FALSE_DOMAIN
        domain = [(f"{prefix}wa_account_id", "in", accounts.ids)]
        if not user.has_group("mail_whatsapp.group_mail_whatsapp_user"):
            domain.append((f"{prefix}whatsapp_user_id", "in", [user.id, False]))
        return domain

    def _whatsapp_accessible_by(self, user):
        domain = self._whatsapp_access_domain(user)
        if domain == expression.TRUE_DOMAIN:
            return self
        if domain == expression.FALSE_DOMAIN:
            return self.browse()
        return (
            self.sudo()
            .with_context(active_test=False)
            .search(expression.AND([[("id", "in", self.ids)], domain]))
            .with_env(self.env)
        )

    def _compute_whatsapp_access_ok(self):
        accessible = self.filtered("id")._whatsapp_accessible_by(self.env.user)
        for channel in self:
            channel.whatsapp_access_ok = channel in accessible

    def _search_whatsapp_access_ok(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search on WhatsApp access."))
        domain = self._whatsapp_access_domain()
        if (operator == "=") == value:
            return domain
        return ["!"] + expression.normalize_domain(domain)

    def _whatsapp_can_manage(self, user=None):
        """True when ``user`` may assign this chat to anyone of its team."""
        self.ensure_one()
        user = user or self.env.user
        if user._is_superuser() or user.has_group(
            "mail_whatsapp.group_mail_whatsapp_admin"
        ):
            return True
        return user.has_group(
            "mail_whatsapp.group_mail_whatsapp_account_manager"
        ) and user in self.wa_account_id.sudo().manager_user_ids

    def _whatsapp_assignable_users(self):
        self.ensure_one()
        return (
            self.wa_account_id.sudo()
            ._whatsapp_team_users()
            .filtered(
                lambda user: user.active
                and user.has_group("mail_whatsapp.group_mail_whatsapp_own")
            )
            .sorted("name")
        )

    def whatsapp_get_assignable_users(self):
        """Return the users this chat can be assigned to by the current user."""
        self.ensure_one()
        self.check_access("read")
        users = self._whatsapp_assignable_users()
        if not self._whatsapp_can_manage():
            free = self.whatsapp_user_id in (self.env.user, self.env["res.users"])
            users = users & self.env.user if free else self.env["res.users"]
        return [{"id": user.id, "name": user.name} for user in users]

    def whatsapp_set_responsible(self, user_id=False):
        """Assign the chat to ``user_id`` or release it with ``False``."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            raise ValidationError(
                _("Only WhatsApp conversations have a responsible.")
            )
        self.check_access("read")
        user = self.env["res.users"].browse(user_id).exists() if user_id else False
        current = self.whatsapp_user_id
        me = self.env.user
        if not self._whatsapp_can_manage():
            takes_free_chat = user == me and current in (me, self.env["res.users"])
            releases_own_chat = not user and current == me
            if not (takes_free_chat or releases_own_chat):
                raise AccessError(
                    _(
                        "You can only take unassigned chats or release your "
                        "own. Ask an Account Administrator to reassign it."
                    )
                )
        if user and user not in self._whatsapp_assignable_users():
            raise ValidationError(
                _(
                    "%(user)s is not an agent of the WhatsApp account %(account)s.",
                    user=user.name,
                    account=self.wa_account_id.sudo().name,
                )
            )
        self._whatsapp_assign(user)
        return Store(self).get_result()

    def action_whatsapp_open_chat(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "mail_whatsapp.action_chats",
            "context": {"active_id": f"discuss.channel_{self.id}"},
        }

    def action_whatsapp_assign(self):
        chats = self.filtered(lambda channel: channel.channel_type == "whatsapp")
        if not chats:
            raise ValidationError(_("Select at least one WhatsApp chat."))
        wizard = self.env["mail.whatsapp.assign"].create(
            {"channel_ids": [Command.set(chats.ids)]}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign Chats"),
            "res_model": "mail.whatsapp.assign",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _whatsapp_assign(self, user):
        self.ensure_one()
        self.sudo().whatsapp_user_id = user or False
        self._whatsapp_sync_team_members()
        self._bus_send_store(self, self._whatsapp_responsible_store_data())

    def _whatsapp_sync_team_members(self):
        """Keep agents as members only while they can see the chat."""
        for channel in self.sudo():
            responsible = channel.whatsapp_user_id
            if (
                responsible
                and responsible.partner_id not in channel.channel_member_ids.partner_id
            ):
                channel.add_members(
                    partner_ids=responsible.partner_id.ids,
                    post_joined_message=False,
                )
            to_remove = channel.env["discuss.channel.member"]
            for member in channel.channel_member_ids:
                users = member.partner_id.user_ids.filtered(lambda u: not u.share)
                if not users or member.partner_id == channel.whatsapp_partner_id:
                    continue
                if not any(channel._whatsapp_accessible_by(u) for u in users):
                    to_remove |= member
            to_remove.unlink()

    def _whatsapp_responsible_store_data(self):
        self.ensure_one()
        user = self.whatsapp_user_id
        return {
            "whatsappResponsibleId": user.id if user else False,
            "whatsappResponsibleName": user.name if user else False,
        }

    @api.depends(
        "whatsapp_partner_id",
        "whatsapp_partner_id.parent_id",
        "whatsapp_partner_id.commercial_partner_id",
        "whatsapp_partner_id.is_company",
    )
    def _compute_whatsapp_company_id(self):
        for channel in self:
            channel.whatsapp_company_id = channel._whatsapp_partner_company()

    def _whatsapp_partner_company(self):
        """Return the company of the WhatsApp person, if they belong to one."""
        self.ensure_one()
        partner = self.whatsapp_partner_id
        if not partner or partner.is_company:
            return partner.browse()
        if partner.parent_id:
            return partner.parent_id
        commercial = partner.commercial_partner_id
        if commercial and commercial != partner:
            return commercial
        return partner.browse()

    def _whatsapp_company_store_data(self):
        self.ensure_one()
        company = self.whatsapp_company_id
        return {
            "whatsappCompanyId": company.id if company else False,
            "whatsappCompanyName": company.display_name if company else False,
        }

    def _whatsapp_auto_assign(self, author):
        """Give an unassigned chat to the first agent who answers it."""
        self.ensure_one()
        if self.whatsapp_user_id or not author:
            return
        user = author.sudo().user_ids.filtered(lambda u: not u.share)[:1]
        if (
            user
            and not user._is_superuser()
            and user in self._whatsapp_assignable_users()
        ):
            self._whatsapp_assign(user)

    def _whatsapp_next_advisor(self):
        """Return the next agent of the account in turn and remember it."""
        self.ensure_one()
        account = self.wa_account_id.sudo()
        candidates = (
            self._whatsapp_assignable_users()
            .filtered(lambda user: not user._is_superuser())
            .sorted("id")
        )
        if not account or not candidates:
            return self.env["res.users"]
        self.env.cr.execute(
            SQL(
                "SELECT id FROM mail_whatsapp_account WHERE id = %s FOR NO KEY UPDATE",
                account.id,
            )
        )
        account.invalidate_recordset(["advisor_last_user_id"])
        last = account.advisor_last_user_id
        following = candidates.filtered(lambda user: user.id > last.id) if last else candidates
        advisor = (following or candidates)[:1]
        account.advisor_last_user_id = advisor
        return advisor

    def _whatsapp_request_advisor(self, reason=False):
        """Hand this chat to an advisor and alert them on WhatsApp.

        A chat that already has a responsible stays with them; otherwise the
        next agent in turn becomes responsible. Return the advisor.
        """
        self.ensure_one()
        if self.channel_type != "whatsapp":
            return self.env["res.users"]
        advisor = self.whatsapp_user_id or self._whatsapp_next_advisor()
        if not advisor:
            self._whatsapp_post_internal_note(
                _("This chat needs an advisor, but its WhatsApp account has no agents.")
            )
            return advisor
        if advisor != self.whatsapp_user_id:
            self._whatsapp_assign(advisor)
        failure = self._whatsapp_notify_advisor(advisor, reason=reason)
        if failure:
            note = _(
                "Chat handed to %(advisor)s. The WhatsApp alert was not sent: "
                "%(failure)s",
                advisor=advisor.name,
                failure=failure,
            )
        else:
            note = _(
                "Chat handed to %(advisor)s, who was alerted on WhatsApp.",
                advisor=advisor.name,
            )
        if reason:
            note = "%s\n%s" % (note, _("Reason: %(reason)s", reason=reason))
        self._whatsapp_post_internal_note(note)
        return advisor

    def _whatsapp_post_internal_note(self, text):
        self.ensure_one()
        return self.sudo().message_post(
            body=tools.plaintext2html(text),
            message_type="notification",
            author_id=self.env.ref("base.partner_root").id,
        )

    def _whatsapp_advisor_alert_text(self, reason=False):
        self.ensure_one()
        lines = [
            _(
                "A WhatsApp customer needs you: %(name)s (+%(number)s).",
                name=self.whatsapp_partner_id.name or self.name,
                number=(self.whatsapp_number or "").lstrip("+"),
            )
        ]
        if reason:
            lines.append(_("Reason: %(reason)s", reason=reason))
        lines.append(
            "%s/odoo/discuss?active_id=discuss.channel_%s"
            % (self.get_base_url(), self.id)
        )
        return "\n".join(lines)

    def _whatsapp_notify_advisor(self, advisor, reason=False):
        """Send a WhatsApp alert about this chat to ``advisor``.

        Return False when sent, or the reason it could not be sent.
        """
        self.ensure_one()
        account = self.wa_account_id.sudo()
        partner = advisor.sudo().partner_id
        number = partner.mobile or partner.phone
        formatted = number and wa_phone_validation.wa_phone_format(
            self.env.company,
            number=number,
            force_format="WHATSAPP",
            raise_exception=False,
        )
        if not formatted:
            return _("%(name)s has no valid mobile number.", name=advisor.name)
        advisor_chat = account._find_active_channel(
            formatted, sender_name=advisor.name, create_if_not_found=True
        )
        if not advisor_chat.whatsapp_user_id and advisor in (
            advisor_chat._whatsapp_assignable_users()
        ):
            advisor_chat._whatsapp_assign(advisor)
        author = self.env.ref("base.partner_root")
        Message = self.env["mail.whatsapp.message"].sudo()
        if advisor_chat.whatsapp_channel_active:
            message = advisor_chat.message_post(
                body=tools.plaintext2html(self._whatsapp_advisor_alert_text(reason)),
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
                author_id=author.id,
            )
            wa_message = Message.search(
                [("mail_message_id", "=", message.id)], limit=1
            )
        elif account.advisor_template_id:
            template = account.advisor_template_id
            message = advisor_chat.with_context(whatsapp_skip_send=True).message_post(
                body=template._get_preview_html(self, include_buttons=False),
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
                author_id=author.id,
            )
            wa_message = Message.create(
                {
                    "mail_message_id": message.id,
                    "message_type": "outbound",
                    "mobile_number": "+%s" % formatted.lstrip("+"),
                    "wa_account_id": account.id,
                    "wa_template_id": template.id,
                    "state": "outgoing",
                    "origin_res_model": self._name,
                    "origin_res_id": self.id,
                    "buttons_data": template._get_resolved_buttons_data(self) or False,
                }
            )
            wa_message._send_message()
        else:
            return _(
                "the 24-hour window with %(name)s is closed and the account has "
                "no Advisor Alert Template.",
                name=advisor.name,
            )
        if not wa_message or wa_message.state == "error":
            return (wa_message.failure_reason if wa_message else False) or _(
                "WhatsApp could not deliver it."
            )
        return False

    def _compute_group_public_id(self):
        wa_channels = self.filtered(lambda channel: channel.channel_type == "whatsapp")
        wa_channels.filtered(lambda channel: not channel.group_public_id).group_public_id = (
            self.env.ref("base.group_user")
        )
        return super(DiscussChannel, self - wa_channels)._compute_group_public_id()

    def _get_notify_valid_parameters(self):
        if self.channel_type == "whatsapp":
            return super()._get_notify_valid_parameters() | {
                "whatsapp_inbound_msg_uid"
            }
        return super()._get_notify_valid_parameters()

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        parent_msg_id = (
            kwargs.pop("parent_msg_id") if "parent_msg_id" in kwargs else False
        )
        if kwargs.get("whatsapp_inbound_msg_uid") and self.channel_type == "whatsapp":
            self.env["mail.whatsapp.message"].sudo().create(
                {
                    "mail_message_id": message.id,
                    "message_type": "inbound",
                    "mobile_number": f"+{self.whatsapp_number}",
                    "msg_uid": kwargs["whatsapp_inbound_msg_uid"],
                    "parent_id": parent_msg_id,
                    "state": "received",
                    "wa_account_id": self.wa_account_id.id,
                }
            )
            if parent_msg_id:
                self.env["mail.whatsapp.message"].sudo().browse(
                    parent_msg_id
                ).state = "replied"
        return super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

    def message_post(
        self,
        *args,
        body="",
        attachment_ids=None,
        message_type="notification",
        parent_id=False,
        **kwargs,
    ):
        post_type = message_type
        if (
            self.channel_type == "whatsapp"
            and message_type == "comment"
            and not kwargs.get("whatsapp_inbound_msg_uid")
            and not self.env.context.get("whatsapp_skip_send")
        ):
            post_type = "whatsapp_message"

        if post_type != "whatsapp_message" or self.channel_type != "whatsapp":
            return super().message_post(
                *args,
                body=body,
                attachment_ids=attachment_ids,
                message_type=message_type,
                parent_id=parent_id,
                **kwargs,
            )

        messages = super().message_post(
            *args,
            body=body,
            message_type=post_type,
            attachment_ids=attachment_ids,
            parent_id=parent_id,
            **kwargs,
        )

        last_message = messages[-1]
        if last_message.author_id == self.whatsapp_partner_id:
            self.last_wa_mail_message_id = last_message
            self._bus_send_store(
                self,
                {
                    "whatsapp_channel_valid_until": self.whatsapp_channel_valid_until,
                },
            )
        elif last_message.author_id:
            self.whatsapp_last_replier_partner_id = last_message.author_id
            self._bus_send_store(
                self,
                {
                    "whatsappLastReplierName": last_message.author_id.name,
                    "whatsappLastReplierPartnerId": last_message.author_id.id,
                },
            )
            self._whatsapp_auto_assign(last_message.author_id)

        should_send = (
            not kwargs.get("whatsapp_inbound_msg_uid")
            and not self.env.context.get("whatsapp_skip_send")
            and messages.author_id != self.whatsapp_partner_id
        )
        if should_send:
            whatsapp_message_vals = []
            for new_msg in messages:
                if not new_msg.wa_message_ids:
                    whatsapp_message_vals.append(
                        {
                            "mail_message_id": new_msg.id,
                            "message_type": "outbound",
                            "mobile_number": f"+{self.whatsapp_number}",
                            "wa_account_id": self.wa_account_id.id,
                        }
                    )
            if whatsapp_message_vals:
                self.env["mail.whatsapp.message"].sudo().create(
                    whatsapp_message_vals
                )._send_message()
        return messages[0] if len(messages) > 1 else messages

    @api.returns("self")
    def _get_whatsapp_channel(
        self,
        whatsapp_number,
        wa_account_id,
        sender_name=False,
        create_if_not_found=False,
    ):
        base_number = (
            whatsapp_number
            if whatsapp_number.startswith("+")
            else f"+{whatsapp_number}"
        )
        wa_number = base_number.lstrip("+")
        wa_formatted = (
            wa_phone_validation.wa_phone_format(
                self.env.company,
                number=base_number,
                force_format="WHATSAPP",
                raise_exception=False,
            )
            or wa_number
        )

        channel = (
            self.sudo()
            .search(
                [
                    ("whatsapp_number", "=", wa_formatted),
                    ("wa_account_id", "=", wa_account_id.id),
                ],
                order="create_date desc",
                limit=1,
            )
        )
        if channel:
            partner = self.env["res.partner"]._find_from_number(wa_formatted)
            if partner:
                channel._sync_whatsapp_partner(partner, wa_formatted)
            elif not channel.whatsapp_partner_id:
                partner = self.env["res.partner"]._find_or_create_from_number(
                    wa_formatted, sender_name
                )
                channel._sync_whatsapp_partner(partner, wa_formatted)
            return channel
        if not create_if_not_found:
            return channel

        partner = self.env["res.partner"]._find_or_create_from_number(
            wa_formatted, sender_name
        )
        channel = (
            self.sudo()
            .with_context(tools.clean_context(self.env.context))
            .create(
                {
                    "name": (partner.name if partner else False) or wa_formatted,
                    "channel_type": "whatsapp",
                    "whatsapp_number": wa_formatted,
                    "whatsapp_partner_id": partner.id,
                    "wa_account_id": wa_account_id.id,
                }
            )
        )
        partners_to_notify = partner
        if wa_account_id.notify_user_ids.partner_id:
            partners_to_notify |= wa_account_id.notify_user_ids.partner_id
        channel.channel_member_ids = [Command.clear()] + [
            Command.create({"partner_id": partner_id.id})
            for partner_id in partners_to_notify
        ]
        channel._broadcast(partners_to_notify.ids)
        return channel

    def _sync_whatsapp_partner(self, partner, wa_formatted):
        """Bind channel to an existing contact matched by phone/mobile."""
        self.ensure_one()
        if not partner:
            return
        current = self.whatsapp_partner_id
        if current == partner:
            if partner.name and self.name in {wa_formatted, f"+{wa_formatted}"}:
                self.sudo().write({"name": partner.name})
            return

        current_name_digits = "".join(c for c in (current.name or "") if c.isdigit())
        wa_digits = "".join(c for c in (wa_formatted or "") if c.isdigit())
        current_looks_auto = (
            not current
            or current.name
            in {
                wa_formatted,
                f"+{wa_formatted}",
                current.mobile,
                current.phone,
            }
            or (current_name_digits and current_name_digits == wa_digits)
        )
        if not current_looks_auto:
            return

        vals = {"whatsapp_partner_id": partner.id}
        if partner.name:
            vals["name"] = partner.name
        self.sudo().write(vals)
        if partner not in self.channel_member_ids.partner_id:
            self.sudo().add_members(partner.ids)
        if current and current != partner and current in self.channel_member_ids.partner_id:
            current_member = self.channel_member_ids.filtered(
                lambda m: m.partner_id == current
            )
            if current_member and current != partner:
                current_member.sudo().unlink()

    def whatsapp_channel_join_and_pin(self):
        """Add the current partner as a member and pin the WhatsApp channel."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            raise ValidationError(
                _("This join method is only available for WhatsApp channels.")
            )

        self.check_access("write")
        current_partner = self.env.user.partner_id
        member = self.channel_member_ids.filtered(
            lambda m: m.partner_id == current_partner
        )
        if member:
            if not member.is_pinned:
                member.write({"unpin_dt": False})
        else:
            new_member = (
                self.env["discuss.channel.member"]
                .with_context(tools.clean_context(self.env.context))
                .sudo()
                .create(
                    {
                        "partner_id": current_partner.id,
                        "channel_id": self.id,
                    }
                )
            )
            message_body = Markup(
                f'<div class="o_mail_notification">{_("joined the channel")}</div>'
            )
            new_member.channel_id.message_post(
                body=message_body,
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
            )
            self._bus_send_store(
                Store(new_member).add(self, {"memberCount": self.member_count})
            )
        return Store(self).get_result()

    def _whatsapp_tags_store_data(self):
        self.ensure_one()
        return [
            {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color or 0,
            }
            for tag in self.whatsapp_tag_ids.sorted("name")
        ]

    def _bus_send_whatsapp_tags(self):
        for channel in self.filtered(lambda c: c.channel_type == "whatsapp"):
            channel._bus_send_store(
                channel,
                {"whatsappTags": channel._whatsapp_tags_store_data()},
            )

    def set_whatsapp_tag_ids(self, tag_ids):
        """Replace WhatsApp tags on this channel and notify Discuss clients."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            raise ValidationError(_("Tags can only be set on WhatsApp conversations."))
        tags = self.env["mail.whatsapp.tag"].browse(tag_ids).exists()
        self.sudo().write({"whatsapp_tag_ids": [Command.set(tags.ids)]})
        self._bus_send_whatsapp_tags()
        return self._whatsapp_tags_store_data()

    def whatsapp_refresh_partner_info(self):
        """Sync channel name from the WhatsApp contact and push to Discuss."""
        self.ensure_one()
        if self.channel_type != "whatsapp":
            return False
        partner = self.whatsapp_partner_id
        vals = {}
        if partner and partner.name and self.name != partner.name:
            vals["name"] = partner.name
        if vals:
            self.sudo().write(vals)
        self._bus_send_store(
            self,
            {
                "name": self.name,
                "whatsapp_partner_id": Store.one(partner, only_id=True)
                if partner
                else False,
                **self._whatsapp_company_store_data(),
            },
        )
        return True

    @api.model
    def whatsapp_focus_search(
        self,
        search_term="",
        limit=30,
        offset=0,
        tag_ids=None,
        replied_by_me=False,
        include_messages=True,
        responsible=False,
    ):
        """Return a page of WhatsApp chats (and optional message hits).

        Contact matches go in ``channel_ids``. Body matches go in ``messages``.
        Designed for incremental loading: use ``offset`` / ``has_more``.
        """
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)
        partner = self.env.user.partner_id
        base_domain = [("channel_type", "=", "whatsapp")]
        if responsible == "me":
            base_domain.append(("whatsapp_user_id", "=", self.env.user.id))
        elif responsible == "none":
            base_domain.append(("whatsapp_user_id", "=", False))
        if replied_by_me:
            base_domain.append(
                ("whatsapp_last_replier_partner_id", "=", partner.id)
            )
        if tag_ids:
            base_domain.append(("whatsapp_tag_ids", "in", list(tag_ids)))

        term = (search_term or "").strip()
        message_hits = self.env["mail.message"]
        order = "last_interest_dt desc, id desc"
        if not term:
            # Fetch limit+1 to know if another page exists without a count query.
            channels = self.search(
                base_domain, limit=limit + 1, offset=offset, order=order
            )
        else:
            match_domains = [
                [("name", "ilike", term)],
                [("whatsapp_number", "ilike", term)],
                [("whatsapp_partner_id.name", "ilike", term)],
                [("whatsapp_partner_id.mobile", "ilike", term)],
                [("whatsapp_partner_id.phone", "ilike", term)],
                [("whatsapp_company_id.name", "ilike", term)],
                [("whatsapp_tag_ids.name", "ilike", term)],
                [("whatsapp_last_replier_partner_id.name", "ilike", term)],
            ]
            digits = "".join(c for c in term if c.isdigit())
            if len(digits) >= 3:
                match_domains.append([("whatsapp_number", "ilike", digits)])
                match_domains.append(
                    [("whatsapp_partner_id.mobile", "ilike", digits)]
                )
                match_domains.append(
                    [("whatsapp_partner_id.phone", "ilike", digits)]
                )
            channels = self.search(
                expression.AND([base_domain, expression.OR(match_domains)]),
                limit=limit + 1,
                offset=offset,
                order=order,
            )
            if include_messages and offset == 0:
                message_hits = self._whatsapp_focus_search_messages(
                    term, partner, limit=limit
                )

        has_more = len(channels) > limit
        channels = channels[:limit]

        channels_for_store = channels
        if message_hits:
            channels_for_store |= self.browse(message_hits.mapped("res_id")).exists()

        store = Store()
        store.add(channels_for_store)
        # Keep list payload light: previews only, no full message store insert.
        last_messages = channels_for_store._get_last_messages()
        last_by_channel = {message.res_id: message for message in last_messages}
        previews = {}
        for channel in channels_for_store:
            message = last_by_channel.get(channel.id)
            if not message:
                continue
            body = tools.html2plaintext(message.body or "").strip()
            if len(body) > 160:
                body = "%s…" % body[:157]
            previews[channel.id] = {
                "body": body,
                "date": fields.Datetime.to_string(message.date)
                if message.date
                else False,
                "message_id": message.id,
                "has_attachment": bool(message.attachment_ids),
            }

        channel_by_id = {channel.id: channel for channel in channels_for_store}
        messages_data = []
        for message in message_hits:
            channel = channel_by_id.get(message.res_id) or self.browse(message.res_id)
            body = tools.html2plaintext(message.body or "").strip()
            if len(body) > 160:
                body = "%s…" % body[:157]
            messages_data.append(
                {
                    "id": message.id,
                    "channel_id": message.res_id,
                    "channel_name": channel.display_name,
                    "body": body,
                    "author_name": message.author_id.name if message.author_id else "",
                    "date": fields.Datetime.to_string(message.date)
                    if message.date
                    else False,
                }
            )

        return {
            "data": store.get_result(),
            "channel_ids": channels.ids,
            "messages": messages_data,
            "previews": previews,
            "has_more": has_more,
            "offset": offset,
            "limit": limit,
        }

    @api.model
    def _whatsapp_focus_search_messages(self, term, partner, limit=30):
        """Search message bodies in the WhatsApp chats the user may see."""
        del partner
        limit = min(max(int(limit or 30), 1), 100)
        term = (term or "").strip()
        if not term:
            return self.env["mail.message"]
        channel_ids = self.search([("channel_type", "=", "whatsapp")]).ids
        if not channel_ids:
            return self.env["mail.message"]
        self.env.cr.execute(
            """
            SELECT message.id
              FROM mail_message AS message
             WHERE message.model = 'discuss.channel'
               AND message.message_type != 'notification'
               AND message.res_id = ANY(%s)
               AND message.body ILIKE %s
             ORDER BY message.id DESC
             LIMIT %s
            """,
            (channel_ids, f"%{term}%", limit),
        )
        ids = [row[0] for row in self.env.cr.fetchall()]
        return self.env["mail.message"].browse(ids).exists()

    def _to_store(self, store: Store):
        super()._to_store(store)
        for channel in self.filtered(lambda c: c.channel_type == "whatsapp"):
            store.add(
                channel,
                {
                    "whatsapp_channel_valid_until": channel.whatsapp_channel_valid_until,
                    "whatsapp_partner_id": Store.one(
                        channel.whatsapp_partner_id, only_id=True
                    ),
                    "whatsappLastReplierName": (
                        channel.whatsapp_last_replier_partner_id.name
                        if channel.whatsapp_last_replier_partner_id
                        else False
                    ),
                    "whatsappLastReplierPartnerId": (
                        channel.whatsapp_last_replier_partner_id.id
                        if channel.whatsapp_last_replier_partner_id
                        else False
                    ),
                    "whatsappTags": channel._whatsapp_tags_store_data(),
                    **channel._whatsapp_responsible_store_data(),
                    **channel._whatsapp_company_store_data(),
                    "whatsappNumber": (
                        "+%s" % channel.whatsapp_number.lstrip("+")
                        if channel.whatsapp_number
                        else False
                    ),
                },
            )

    def _types_allowing_seen_infos(self):
        return super()._types_allowing_seen_infos() + ["whatsapp"]

    def execute_command_leave(self, **kwargs):
        if self.channel_type == "whatsapp":
            self.action_unfollow()
        else:
            super().execute_command_leave(**kwargs)
