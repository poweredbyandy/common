import { Component, onMounted, onWillUnmount, status, useRef, useState } from "@odoo/owl";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { buildZXingBarcodeDetector } from "@web/core/barcode/ZXingBarcodeDetector";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";

export class AutoOrder extends Component {
    static template = "web_sale_auto_order.AutoOrder";
    static props = {
        cart: { type: Object, optional: true },
        companyCurrencyName: { type: String, optional: true },
        pricelistCurrencyName: { type: String, optional: true },
        sameCurrency: { type: Boolean, optional: true },
        product: { type: Object, optional: true },
        scanError: { type: String, optional: true },
        scanCode: { type: String, optional: true },
        buttonColor: { type: String, optional: true },
        buttonTextColor: { type: String, optional: true },
    };

    setup() {
        this.scannerSupported = isBarcodeScannerSupported();
        this.scanDelay = 1800;
        this.videoRef = useRef("videoPreview");
        this.stream = null;
        this.detector = null;
        this.detectTimeout = null;
        this.state = useState({
            cart: this.props.cart || this._emptyCart(),
            product: this.props.product || null,
            quantity: 1,
            manualCode: "",
            loading: false,
            error: this.props.scanError || "",
            scannerError: "",
            cameraOn: false,
            cameraStarting: false,
            confirmClear: false,
            notesExpanded: false,
            totalsExpanded: false,
            success: null,
            registerVat: "",
            registerName: "",
            registerPhone: "",
            registerEmail: "",
            registerError: "",
            registerVatExists: null,
            registerFoundName: "",
            busy: false,
            ready: true,
            allowImages: false,
            loadedImages: {},
        });
        onMounted(() => {
            this._removeBootLoader();
            this.bootstrap();
        });
        onWillUnmount(() => this._stopStream());
    }

    _removeBootLoader() {
        const boot = document.getElementById("o_wsao_boot");
        if (boot) {
            boot.remove();
        }
    }

    async bootstrap() {
        try {
            const result = await rpc("/auto-order/cart", {});
            if (result.cart) {
                this.state.cart = result.cart;
                this._deferImages();
            }
            if (this.props.scanCode) {
                await this.lookupCode(this.props.scanCode);
                this._clearScanCodeFromUrl();
            } else if (this.props.product || this.props.scanError) {
                this._clearScanCodeFromUrl();
            }
        } catch {
            this.state.error = _t("Could not load the page.");
        }
    }

    _clearScanCodeFromUrl() {
        const url = new URL(browser.location.href);
        if (!url.searchParams.has("code")) {
            return;
        }
        url.searchParams.delete("code");
        const next = url.pathname + url.search + url.hash;
        browser.history.replaceState({}, "", next);
    }

    get showScanner() {
        return this.scannerSupported && this.state.cameraOn && !this.state.scannerError;
    }

    get canCheckout() {
        return Boolean(this.state.cart && this.state.cart.line_count);
    }

    get showDualCurrency() {
        const cart = this.state.cart || {};
        if (this.state.product) {
            return !this.state.product.same_currency;
        }
        return !cart.same_currency;
    }

    get cartItemsLabel() {
        return _t("%s items", this.state.cart.line_count || 0);
    }

    get buyLabel() {
        return _t("Buy (%s)", this.state.cart.line_count || 0);
    }

    _deferImages() {
        this.state.allowImages = false;
        browser.requestAnimationFrame(() => {
            browser.requestAnimationFrame(() => {
                this.state.allowImages = true;
            });
        });
    }

    markImageReady(url) {
        if (!url) {
            return;
        }
        this.state.loadedImages[url] = true;
    }

    isImageReady(url) {
        return Boolean(url && this.state.loadedImages[url]);
    }

    _emptyCart() {
        return {
            order_id: false,
            line_count: 0,
            lines: [],
            same_currency: true,
            rateLabel: "",
            company_currency_name: this.props.companyCurrencyName || "",
            pricelist_currency_name: this.props.pricelistCurrencyName || "",
            amount_company_untaxed_formatted: "",
            amount_company_taxed_formatted: "",
            amount_pricelist_untaxed_formatted: "",
            amount_pricelist_taxed_formatted: "",
        };
    }

    onScan(code) {
        if (this.state.success || this.state.product || this.state.loading || this.state.busy) {
            return;
        }
        this.lookupCode(code);
    }

    onScanError(error) {
        this._stopStream();
        this.state.cameraOn = false;
        this.state.cameraStarting = false;
        this.state.scannerError = error && error.message ? error.message : _t("Camera is not available.");
    }

    _stopStream() {
        if (this.detectTimeout) {
            browser.clearTimeout(this.detectTimeout);
            this.detectTimeout = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        const video = this.videoRef.el;
        if (video) {
            video.srcObject = null;
        }
    }

    _rearCameraDevice(devices) {
        const videos = (devices || []).filter((device) => device.kind === "videoinput");
        if (!videos.length) {
            return null;
        }
        const rear = videos.find((device) =>
            /back|rear|environment|trasera/i.test(device.label || "")
        );
        if (rear) {
            return rear;
        }
        const front = videos.find((device) =>
            /front|user|face|frontal/i.test(device.label || "")
        );
        if (front && videos.length > 1) {
            return videos.find((device) => device.deviceId !== front.deviceId) || videos[videos.length - 1];
        }
        return null;
    }

    async _requestRearCameraStream(mediaDevices) {
        const attempts = [
            { video: { facingMode: { exact: "environment" } }, audio: false },
            { video: { facingMode: { ideal: "environment" } }, audio: false },
            { video: { facingMode: "environment" }, audio: false },
            { video: true, audio: false },
        ];
        let stream;
        let lastError;
        for (const constraints of attempts) {
            try {
                stream = await mediaDevices.getUserMedia(constraints);
                break;
            } catch (err) {
                lastError = err;
                if (err && err.name === "NotAllowedError") {
                    throw err;
                }
            }
        }
        if (!stream) {
            throw lastError || new Error(_t("Camera is not available."));
        }
        const track = stream.getVideoTracks()[0];
        const settings = track && track.getSettings ? track.getSettings() : {};
        if (settings.facingMode === "environment") {
            return stream;
        }
        let devices = [];
        try {
            devices = await mediaDevices.enumerateDevices();
        } catch {
            return stream;
        }
        const rear = this._rearCameraDevice(devices);
        if (!rear || rear.deviceId === settings.deviceId) {
            return stream;
        }
        stream.getTracks().forEach((item) => item.stop());
        await delay(250);
        return mediaDevices.getUserMedia({
            video: { deviceId: { exact: rear.deviceId }, facingMode: { ideal: "environment" } },
            audio: false,
        });
    }

    async _bindVideoStream(stream) {
        const video = this.videoRef.el;
        if (!video) {
            throw new Error(_t("Camera is not available."));
        }
        video.setAttribute("playsinline", "true");
        video.setAttribute("webkit-playsinline", "true");
        video.setAttribute("autoplay", "true");
        video.playsInline = true;
        video.muted = true;
        video.srcObject = stream;
        if (video.readyState < 2) {
            await Promise.race([
                new Promise((resolve) => {
                    const onReady = () => {
                        video.removeEventListener("loadedmetadata", onReady);
                        resolve();
                    };
                    video.addEventListener("loadedmetadata", onReady);
                }),
                delay(1500),
            ]);
        }
        try {
            await video.play();
        } catch {
            return;
        }
    }

    async _waitForZXing() {
        if (window.ZXing) {
            return;
        }
        const deadline = Date.now() + 20000;
        while (!window.ZXing && Date.now() < deadline) {
            await delay(80);
        }
        if (!window.ZXing) {
            throw new Error(_t("The barcode scanner library could not be loaded."));
        }
    }

    async _ensureDetector() {
        if (this.detector) {
            return;
        }
        if ("BarcodeDetector" in window) {
            try {
                const formats = await window.BarcodeDetector.getSupportedFormats();
                this.detector = new window.BarcodeDetector({ formats });
                return;
            } catch {
                this.detector = null;
            }
        }
        await this._waitForZXing();
        const DetectorClass = buildZXingBarcodeDetector(window.ZXing);
        const formats = await DetectorClass.getSupportedFormats();
        this.detector = new DetectorClass({ formats });
    }

    async _detectTick() {
        if (status(this) === "destroyed" || !this.stream || !this.state.cameraOn) {
            return;
        }
        const video = this.videoRef.el;
        if (video && this.detector) {
            try {
                const codes = await this.detector.detect(video);
                const value = codes && codes.length && codes[0].rawValue;
                if (value) {
                    this.onScan(value);
                    await delay(this.scanDelay);
                }
            } catch {
                return this._scheduleDetect();
            }
        }
        this._scheduleDetect();
    }

    _scheduleDetect() {
        if (status(this) === "destroyed" || !this.stream || !this.state.cameraOn) {
            return;
        }
        this.detectTimeout = browser.setTimeout(() => this._detectTick(), 120);
    }

    async startCamera() {
        if (this.state.cameraStarting || this.state.cameraOn) {
            return;
        }
        this.state.scannerError = "";
        const mediaDevices = browser.navigator.mediaDevices;
        if (!mediaDevices || !mediaDevices.getUserMedia) {
            this.state.scannerError = _t("Camera is not available.");
            return;
        }
        this.state.cameraStarting = true;
        try {
            const stream = await this._requestRearCameraStream(mediaDevices);
            if (status(this) === "destroyed") {
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            this.stream = stream;
            await this._bindVideoStream(stream);
            this.state.cameraOn = true;
            this._ensureDetector()
                .then(() => this._scheduleDetect())
                .catch((error) => this.onScanError(error));
        } catch (err) {
            this._stopStream();
            this.state.cameraOn = false;
            this.state.scannerError = err && err.message
                ? err.message
                : _t("Camera is not available.");
        } finally {
            this.state.cameraStarting = false;
        }
    }

    stopCamera() {
        this._stopStream();
        this.state.cameraOn = false;
        this.state.cameraStarting = false;
        this.state.scannerError = "";
    }

    onManualSubmit(ev) {
        ev.preventDefault();
        const code = (this.state.manualCode || "").trim();
        if (!code || this.state.loading) {
            return;
        }
        this.lookupCode(code);
    }

    async lookupCode(code) {
        this.state.loading = true;
        this.state.error = "";
        try {
            const result = await rpc("/auto-order/scan", { code });
            if (result.error) {
                this.state.error = result.error;
                this.state.product = null;
                return;
            }
            this.state.product = result.product;
            this.state.quantity = result.product.quantity || 1;
            this.state.manualCode = "";
            this.state.notesExpanded = false;
            this._deferImages();
        } catch {
            this.state.error = _t("Could not look up this code.");
        } finally {
            this.state.loading = false;
        }
    }

    changeQuantity(delta) {
        const current = parseInt(this.state.quantity, 10) || 1;
        const next = current + delta;
        this.state.quantity = next < 1 ? 1 : next;
    }

    onQuantityInput(ev) {
        const raw = String(ev.target.value || "").replace(/[^\d]/g, "");
        if (raw === "" && ev.type === "input") {
            this.state.quantity = "";
            return;
        }
        const next = parseInt(raw, 10);
        this.state.quantity = !next || next < 1 ? 1 : next;
    }

    _productQuantity() {
        const quantity = parseInt(this.state.quantity, 10);
        return !quantity || quantity < 1 ? 1 : quantity;
    }

    get notesLong() {
        const notes = this.state.product && this.state.product.internal_notes;
        if (!notes) {
            return false;
        }
        return notes.length > 140 || notes.split(/\n/).length > 4;
    }

    toggleNotes() {
        this.state.notesExpanded = !this.state.notesExpanded;
    }

    toggleTotals() {
        this.state.totalsExpanded = !this.state.totalsExpanded;
    }

    get totalsToggleLabel() {
        return this.state.totalsExpanded ? _t("Hide details") : _t("Show details");
    }

    get themeStyle() {
        const accent = this.props.buttonColor || "#10b981";
        const ink = this.props.buttonTextColor || "#052e16";
        return `--wsao-accent: ${accent}; --wsao-accent-ink: ${ink};`;
    }

    cancelProduct() {
        this.state.product = null;
        this.state.quantity = 1;
        this.state.error = "";
        this.state.notesExpanded = false;
    }

    async confirmAdd() {
        if (!this.state.product || this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.error = "";
        try {
            const result = await rpc("/auto-order/cart/add", {
                product_id: this.state.product.id,
                set_qty: this._productQuantity(),
                line_id: this.state.product.line_id || null,
            });
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.cart = result.cart;
            this.state.product = null;
            this.state.quantity = 1;
            this._deferImages();
        } catch {
            this.state.error = _t("Could not add the product to the cart.");
        } finally {
            this.state.busy = false;
        }
    }

    async updateLineQty(line, delta) {
        const setQty = (line.quantity || 0) + delta;
        return this._setLineQty(line, setQty < 0 ? 0 : setQty);
    }

    async removeLine(line) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await rpc("/auto-order/cart/line/remove", {
                line_id: line.id,
            });
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.cart = result.cart;
        } catch {
            this.state.error = _t("Could not update the cart.");
        } finally {
            this.state.busy = false;
        }
    }

    async _setLineQty(line, setQty) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await rpc("/auto-order/cart/update", {
                line_id: line.id,
                set_qty: setQty,
            });
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.cart = result.cart;
        } catch {
            this.state.error = _t("Could not update the cart.");
        } finally {
            this.state.busy = false;
        }
    }

    askClearCart() {
        if (!this.canCheckout) {
            return;
        }
        this.state.confirmClear = true;
    }

    cancelClearCart() {
        this.state.confirmClear = false;
    }

    async clearCart() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.confirmClear = false;
        try {
            const result = await rpc("/auto-order/cart/clear", {});
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.cart = result.cart;
        } catch {
            this.state.error = _t("Could not empty the cart.");
        } finally {
            this.state.busy = false;
        }
    }

    async checkout() {
        if (!this.canCheckout || this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.error = "";
        try {
            const result = await rpc("/auto-order/cart/buy", {});
            if (result.error) {
                this.state.error = result.error;
                return;
            }
            this.state.cart = result.cart || this._emptyCart();
            this.state.product = null;
            this.state.success = {
                orderName: result.orderName || "",
                extraMessage: result.extraMessage || "",
                step: "choice",
            };
            this.state.registerVat = "";
            this.state.registerName = "";
            this.state.registerPhone = "";
            this.state.registerEmail = "";
            this.state.registerError = "";
            this.state.registerVatExists = null;
            this.state.registerFoundName = "";
            this.stopCamera();
        } catch {
            this.state.error = _t("Could not save the order.");
        } finally {
            this.state.busy = false;
        }
    }

    openRegister() {
        if (!this.state.success) {
            return;
        }
        this.state.registerError = "";
        this.state.registerVatExists = null;
        this.state.registerFoundName = "";
        this.state.success.step = "register";
    }

    onRegisterVatInput() {
        this.state.registerVatExists = null;
        this.state.registerFoundName = "";
        this.state.registerError = "";
    }

    skipRegister() {
        if (!this.state.success) {
            return;
        }
        this.state.success.step = "pay";
    }

    async submitRegister(ev) {
        ev.preventDefault();
        if (!this.state.success || this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.registerError = "";
        try {
            if (this.state.registerVatExists === null) {
                const lookup = await rpc("/auto-order/order/lookup-vat", {
                    vat: this.state.registerVat,
                });
                if (lookup.error) {
                    this.state.registerError = lookup.error;
                    return;
                }
                this.state.registerVatExists = Boolean(lookup.exists);
                this.state.registerFoundName = lookup.exists ? lookup.name || "" : "";
                return;
            }
            if (this.state.registerVatExists === true) {
                const linked = await rpc("/auto-order/order/register", {
                    vat: this.state.registerVat,
                });
                if (linked.error) {
                    this.state.registerError = linked.error;
                    return;
                }
                this.state.success.step = "pay";
                return;
            }
            const result = await rpc("/auto-order/order/register", {
                vat: this.state.registerVat,
                name: this.state.registerName,
                phone: this.state.registerPhone,
                email: this.state.registerEmail,
            });
            if (result.error) {
                this.state.registerError = result.error;
                return;
            }
            this.state.success.step = "pay";
        } catch {
            this.state.registerError = _t("Could not save your information.");
        } finally {
            this.state.busy = false;
        }
    }

    async finishOrder() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await rpc("/auto-order/order/finish", {});
            if (result.cart) {
                this.state.cart = result.cart;
            } else {
                this.state.cart = this._emptyCart();
            }
        } catch {
            this.state.cart = this._emptyCart();
        } finally {
            this.state.success = null;
            this.state.registerVat = "";
            this.state.registerName = "";
            this.state.registerPhone = "";
            this.state.registerEmail = "";
            this.state.registerError = "";
            this.state.registerVatExists = null;
            this.state.registerFoundName = "";
            this.state.busy = false;
        }
    }
}

registry.category("public_components").add("web_sale_auto_order.AutoOrder", AutoOrder);
