from odoo import http
from odoo.http import request


class ResUsersUserController(http.Controller):

    @http.route(
        "/res_users_user/session",
        type="json",
        auth="user",
        readonly=True,
    )
    def session_info(self):
        return request.env.user.res_users_user_get_session()

    @http.route("/res_users_user/login", type="json", auth="user")
    def login(self, sub_user_id, pin):
        return request.env.user.res_users_user_login(sub_user_id, pin)

    @http.route("/res_users_user/lock", type="json", auth="user")
    def lock(self):
        return request.env.user.res_users_user_lock()
