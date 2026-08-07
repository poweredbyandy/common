import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.osv import expression

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
    ):
        """Return a page of WhatsApp chats (and optional message hits).

        Contact matches go in ``channel_ids``. Body matches go in ``messages``.
        Designed for incremental loading: use ``offset`` / ``has_more``.
        """
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)
        partner = self.env.user.partner_id
        base_domain = [
            ("channel_type", "=", "whatsapp"),
            ("channel_member_ids.partner_id", "=", partner.id),
        ]
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
        """Search message bodies in WhatsApp channels the user belongs to."""
        limit = min(max(int(limit or 30), 1), 100)
        term = (term or "").strip()
        if not term:
            return self.env["mail.message"]
        self.env.cr.execute(
            """
            SELECT message.id
              FROM mail_message AS message
              JOIN discuss_channel AS channel
                ON channel.id = message.res_id
              JOIN discuss_channel_member AS member
                ON member.channel_id = channel.id
             WHERE message.model = 'discuss.channel'
               AND message.message_type != 'notification'
               AND channel.channel_type = 'whatsapp'
               AND member.partner_id = %s
               AND message.body ILIKE %s
             ORDER BY message.id DESC
             LIMIT %s
            """,
            (partner.id, f"%{term}%", limit),
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
