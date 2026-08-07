/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useState,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const FB_SDK_SCRIPT_ID = "facebook-jssdk";
const FB_SDK_URL = "https://connect.facebook.net/en_US/sdk.js";

function rpcErrorMessage(error, fallback) {
    return (
        error?.data?.message ||
        error?.message ||
        error?.data?.arguments?.[0] ||
        (typeof error === "string" ? error : "") ||
        fallback
    );
}

export class MailWhatsappEmbeddedSignupAction extends Component {
    static template = "mail_whatsapp.EmbeddedSignupAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.sessionData = { code: null, wabaId: null, phoneNumberId: null };
        this.state = useState({
            loading: true,
            sdkReady: false,
            configured: false,
            missing: [],
            connecting: false,
            error: "",
            config: {},
            fbStatus: "",
            fbUserId: "",
            fbStatusChecking: false,
            permissions: [],
            grantedPermissions: [],
            declinedPermissions: [],
            permissionsLoading: false,
            rerequesting: false,
        });
        onWillStart(() => this._loadConfigAndSdk());
        onMounted(() => {
            this._registerGlobalLoginCallbacks();
        });
        onWillUnmount(() => {
            this._unregisterGlobalLoginCallbacks();
            this._removeSessionMessageHandler();
        });
    }

    get hasDeclinedPermissions() {
        return this.state.declinedPermissions.length > 0;
    }

    async _loadConfigAndSdk() {
        this.state.loading = true;
        this.state.error = "";
        this.state.sdkReady = false;
        this.state.fbStatus = "";
        this.state.fbUserId = "";
        this._clearPermissions();
        try {
            const config = await this.orm.call(
                "mail.whatsapp.account",
                "get_embedded_signup_config",
                []
            );
            this.state.config = config || {};
            this.state.configured = Boolean(config?.configured);
            this.state.missing = Array.isArray(config?.missing) ? config.missing : [];
            if (!this.state.configured) {
                return;
            }
            await this._ensureFacebookSdk();
            this.state.sdkReady = true;
            await this._refreshLoginStatus();
        } catch (error) {
            this.state.sdkReady = false;
            this.state.error = rpcErrorMessage(
                error,
                _t("Unable to load Embedded Signup configuration.")
            );
        } finally {
            this.state.loading = false;
        }
    }

    _clearPermissions() {
        this.state.permissions = [];
        this.state.grantedPermissions = [];
        this.state.declinedPermissions = [];
    }

    /**
     * Facebook Login for Business / Embedded Signup requires authorization
     * code grant. Default SDK response_type=token is rejected by Meta.
     */
    _getLoginOptions({ coexistence = false, rerequest = false } = {}) {
        const options = {
            config_id: this.state.config.config_id,
            response_type: "code",
            override_default_response_type: true,
            extras: {
                setup: {},
                sessionInfoVersion: "3",
            },
        };
        if (coexistence) {
            options.extras.featureType = "whatsapp_business_app_onboarding";
        }
        if (rerequest) {
            options.auth_type = "rerequest";
        }
        return options;
    }

    _registerGlobalLoginCallbacks() {
        window.checkLoginState = () => {
            this.checkLoginState();
        };
        window.statusChangeCallback = (response) => {
            this._statusChangeCallback(response);
        };
    }

    _unregisterGlobalLoginCallbacks() {
        if (window.checkLoginState) {
            delete window.checkLoginState;
        }
        if (window.statusChangeCallback) {
            delete window.statusChangeCallback;
        }
    }

    _statusChangeCallback(response, { autoComplete = false } = {}) {
        this.state.fbStatus = response?.status || "unknown";
        this.state.fbUserId = response?.authResponse?.userID || "";
        if (response?.status === "connected") {
            this._refreshPermissions();
        } else {
            this._clearPermissions();
        }
        if (autoComplete && response?.authResponse?.code && !this.state.connecting) {
            this.sessionData.code = response.authResponse.code;
            this._handleFacebookLoginResponse(response, this.sessionData);
        }
    }

    checkLoginState() {
        this.state.fbStatusChecking = true;
        if (!window.FB?.getLoginStatus) {
            this.state.fbStatus = "sdk_missing";
            this.state.fbStatusChecking = false;
            return;
        }
        window.FB.getLoginStatus((response) => {
            this._statusChangeCallback(response, { autoComplete: false });
            this.state.fbStatusChecking = false;
        });
    }

    _refreshLoginStatus() {
        this.state.fbStatusChecking = true;
        return new Promise((resolve) => {
            if (!window.FB?.getLoginStatus) {
                this.state.fbStatus = "sdk_missing";
                this.state.fbStatusChecking = false;
                resolve();
                return;
            }
            window.FB.getLoginStatus((response) => {
                this._statusChangeCallback(response, { autoComplete: false });
                this.state.fbStatusChecking = false;
                resolve(response);
            });
        });
    }

    onCheckLoginStatus() {
        this.checkLoginState();
    }

    _refreshPermissions() {
        if (!window.FB?.api) {
            this._clearPermissions();
            return Promise.resolve([]);
        }
        this.state.permissionsLoading = true;
        return new Promise((resolve) => {
            // With response_type=code there may be no user access token in the
            // browser; Graph /me/permissions then fails until a session exists.
            window.FB.api("/me/permissions", (response) => {
                if (response?.error) {
                    this._clearPermissions();
                    this.state.permissionsLoading = false;
                    resolve([]);
                    return;
                }
                const rows = Array.isArray(response?.data) ? response.data : [];
                this.state.permissions = rows;
                this.state.grantedPermissions = rows
                    .filter((row) => row.status === "granted")
                    .map((row) => row.permission);
                this.state.declinedPermissions = rows
                    .filter((row) => row.status === "declined")
                    .map((row) => row.permission);
                this.state.permissionsLoading = false;
                resolve(rows);
            });
        });
    }

    onRefreshPermissions() {
        this._refreshPermissions();
    }

    onRerequestDeclinedPermissions() {
        if (!this.state.declinedPermissions.length || !window.FB?.login) {
            return;
        }
        this.state.rerequesting = true;
        this.state.error = "";
        window.FB.login(
            (response) => {
                this.state.rerequesting = false;
                this.state.fbStatus = response?.status || this.state.fbStatus;
                this.state.fbUserId =
                    response?.authResponse?.userID || this.state.fbUserId;
                if (response?.authResponse?.code) {
                    this.sessionData = {
                        code: response.authResponse.code,
                        wabaId: null,
                        phoneNumberId: null,
                    };
                    this._handleFacebookLoginResponse(response, this.sessionData);
                    return;
                }
                this._refreshPermissions().then(() => {
                    if (this.state.declinedPermissions.length) {
                        this.notification.add(
                            _t(
                                "Some permissions are still declined. Complete Embedded Signup again if WhatsApp access is missing."
                            ),
                            { type: "warning" }
                        );
                    } else {
                        this.notification.add(_t("Permissions updated."), {
                            type: "success",
                        });
                    }
                });
            },
            this._getLoginOptions({ coexistence: true, rerequest: true })
        );
    }

    _graphVersion() {
        const version = this.state.config.graph_version || "v23.0";
        return version.startsWith("v") ? version : `v${version}`;
    }

    async onOpenSettings() {
        try {
            const action = await this.orm.call(
                "mail.whatsapp.account",
                "action_open_whatsapp_settings",
                []
            );
            await this.action.doAction(action);
        } catch (error) {
            this.state.error = rpcErrorMessage(
                error,
                _t("Unable to open WhatsApp Settings.")
            );
        }
    }

    async onRetry() {
        await this._loadConfigAndSdk();
    }

    _loadFacebookSdkScript() {
        return new Promise((resolve, reject) => {
            if (document.getElementById(FB_SDK_SCRIPT_ID)) {
                if (window.FB?.init) {
                    resolve();
                    return;
                }
                const started = Date.now();
                const timer = setInterval(() => {
                    if (window.FB?.init) {
                        clearInterval(timer);
                        resolve();
                    } else if (Date.now() - started > 15000) {
                        clearInterval(timer);
                        reject(new Error(_t("Facebook SDK load timed out.")));
                    }
                }, 50);
                return;
            }

            const firstScript = document.getElementsByTagName("script")[0];
            const js = document.createElement("script");
            js.id = FB_SDK_SCRIPT_ID;
            js.src = FB_SDK_URL;
            js.async = true;
            js.onload = () => resolve();
            js.onerror = () =>
                reject(
                    new Error(
                        _t(
                            "Failed to load Facebook SDK. Allow connect.facebook.net in CSP and add this domain in the Meta App settings."
                        )
                    )
                );
            if (firstScript?.parentNode) {
                firstScript.parentNode.insertBefore(js, firstScript);
            } else {
                document.head.appendChild(js);
            }
        });
    }

    async _ensureFacebookSdk() {
        const appId = this.state.config.app_id;
        if (!appId) {
            throw new Error(_t("Meta App ID is not configured."));
        }
        if (window.FB?.login && window.__mail_whatsapp_fb_initialized === appId) {
            return;
        }

        await new Promise((resolve, reject) => {
            let settled = false;
            const timeout = setTimeout(() => {
                if (!settled) {
                    settled = true;
                    reject(new Error(_t("Facebook SDK load timed out.")));
                }
            }, 20000);

            const finish = (error) => {
                if (settled) {
                    return;
                }
                settled = true;
                clearTimeout(timeout);
                if (error) {
                    reject(error instanceof Error ? error : new Error(String(error)));
                    return;
                }
                resolve();
            };

            let initStarted = false;
            const runFbInit = () => {
                if (initStarted || window.__mail_whatsapp_fb_initialized === appId) {
                    if (window.__mail_whatsapp_fb_initialized === appId) {
                        finish();
                    }
                    return;
                }
                initStarted = true;
                try {
                    window.FB.init({
                        appId: appId,
                        cookie: true,
                        xfbml: false,
                        version: this._graphVersion(),
                        autoLogAppEvents: true,
                    });
                    if (window.FB.AppEvents?.logPageView) {
                        window.FB.AppEvents.logPageView();
                    }
                    window.__mail_whatsapp_fb_initialized = appId;
                    finish();
                } catch (error) {
                    finish(error);
                }
            };

            window.fbAsyncInit = runFbInit;

            this._loadFacebookSdkScript()
                .then(() => {
                    if (window.FB?.init) {
                        runFbInit();
                    }
                })
                .catch(finish);
        });

        if (!window.FB?.login) {
            throw new Error(
                _t("Facebook SDK loaded but FB.login is unavailable.")
            );
        }
    }

    _addSessionMessageHandler(sessionData) {
        this._removeSessionMessageHandler();
        this._sessionMessageHandler = (event) => {
            if (!event?.origin?.endsWith?.("facebook.com")) {
                return;
            }
            try {
                const data = JSON.parse(event.data);
                if (data.type !== "WA_EMBEDDED_SIGNUP") {
                    return;
                }
                if (
                    data.event === "FINISH" ||
                    data.event === "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING"
                ) {
                    sessionData.wabaId = data.data?.waba_id || sessionData.wabaId;
                    sessionData.phoneNumberId =
                        data.data?.phone_number_id || sessionData.phoneNumberId;
                }
            } catch {
                // Non-JSON postMessage payloads from the SDK can be ignored.
            }
        };
        window.addEventListener("message", this._sessionMessageHandler);
    }

    _removeSessionMessageHandler() {
        if (this._sessionMessageHandler) {
            window.removeEventListener("message", this._sessionMessageHandler);
            this._sessionMessageHandler = null;
        }
    }

    onConnect() {
        this.state.connecting = true;
        this.state.error = "";
        this.sessionData = { code: null, wabaId: null, phoneNumberId: null };

        this._ensureFacebookSdk()
            .then(() => {
                this.state.sdkReady = true;
                this._addSessionMessageHandler(this.sessionData);
                window.FB.login(
                    (response) => {
                        this._removeSessionMessageHandler();
                        this._handleFacebookLoginResponse(response, this.sessionData);
                    },
                    this._getLoginOptions({ coexistence: true })
                );
            })
            .catch((error) => {
                this._removeSessionMessageHandler();
                this.state.connecting = false;
                this.state.sdkReady = false;
                this.state.error = rpcErrorMessage(
                    error,
                    _t("Unable to open Facebook Embedded Signup.")
                );
            });
    }

    _handleFacebookLoginResponse(response, sessionData) {
        this.state.fbStatus = response?.status || this.state.fbStatus;
        this.state.fbUserId =
            response?.authResponse?.userID || this.state.fbUserId || "";
        sessionData.code = response?.authResponse?.code || sessionData.code;
        if (!sessionData.code) {
            this.state.connecting = false;
            if (response?.status === "connected") {
                this.state.error = _t(
                    "Facebook session is connected, but no Embedded Signup authorization code was returned. Close other Facebook popups and try Continue with Facebook again."
                );
            } else {
                this.state.error = _t(
                    "Embedded Signup finished without an authorization code. If you closed the popup or declined permissions, try again."
                );
            }
            return;
        }
        this.state.connecting = true;
        this.orm
            .call("mail.whatsapp.account", "complete_embedded_signup", [
                sessionData.code,
                sessionData.wabaId || false,
                sessionData.phoneNumberId || false,
                response?.authResponse?.userID || this.state.fbUserId || false,
                response?.authResponse?.accessToken || false,
            ])
            .then((action) => {
                this.notification.add(_t("WhatsApp account connected."), {
                    type: "success",
                });
                this.state.connecting = false;
                if (action) {
                    return this.action.doAction(action);
                }
            })
            .catch((error) => {
                this.state.connecting = false;
                this.state.error = rpcErrorMessage(error, _t("Onboarding failed."));
            });
    }
}

registry
    .category("actions")
    .add("mail_whatsapp_embedded_signup", MailWhatsappEmbeddedSignupAction);
