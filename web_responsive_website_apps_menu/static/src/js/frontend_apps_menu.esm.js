/** @odoo-module **/

export const OPEN_APPS_MENU_STORAGE_KEY = "web_responsive_open_apps_menu";

document.addEventListener("DOMContentLoaded", () => {
    const button = document.querySelector(".o_frontend_to_backend_apps_btn");
    if (!button) {
        return;
    }
    button.addEventListener("click", () => {
        window.sessionStorage.setItem(OPEN_APPS_MENU_STORAGE_KEY, "1");
    });
});
