/** @odoo-module **/
/* global Sha1 */
import { PosStore } from "@point_of_sale/app/store/pos_store";
import {
    Order,
    Orderline
} from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(loadedData);
        this.workInProduct = this.db.product_by_id[loadedData['product_product_work_in']];
        this.workOutProduct = this.db.product_by_id[loadedData['product_product_work_out']]
    },
    useBlackBoxBe() {
        return this.config.iface_fiscal_data_module;
    },
    checkIfUserClocked() {
        const cashierId = this.get_cashier().id;
        if (this.config.module_pos_hr) {
            return this.pos_session.employees_clocked_ids.find(elem => elem === cashierId);
        }
        return this.pos_session.users_clocked_ids.find(elem => elem === cashierId);
    },
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange();
        return this.useBlackBoxBe() || result;
    },
    doNotAllowRefundAndSales() {
        const result = super.doNotAllowRefundAndSales();
        return this.useBlackBoxBe() || result;
    },
    async pushProFormaOrder(order) {
        order.receipt_type = order.get_total_with_tax() >= 0 ? "PS" : "PR";
        await this.sendDraftToServer();
        await this.pushToBlackbox(order);
    },
    async pushToBlackbox(order) {
        try {
            const data = await this.pushDataToBlackbox(this.createOrderDataForBlackbox(order));
            if (data.value.error && data.value.error.errorCode != "000000") {
                throw data.value.error;
            }
            this.setDataForPushOrderFromBlackbox(order, data);
        } catch (err) {
            console.log(err);
            if (err.errorCode === "202000") { // need to be tested
                const { confirmed, payload } = await this.popup.add(NumberPopup, {
                    startingValue: 0,
                    title: _t("Enter pin code:"),
                });

                if (!confirmed)
                    return;
                this.pushDataToBlackbox(this.createPinCodeDataForBlackbox(payload));
            } else {
                // other errors
                this.env.services.popup.add(ErrorPopup, {
                    title: _t("Blackbox error"),
                    body: _t(err.status ? err.status : "Internal blackbox error"),
                });
                return;
            }
        }
    },
    async push_single_order(order, opts) {
        if (this.useBlackBoxBe() && order) {
            order.receipt_type = false;
            await this.pushToBlackbox(order);
        }
        return await super.push_single_order(order, opts);
    },
    createPinCodeDataForBlackbox(code) {
        return "P040" + code;
    },
    createOrderDataForBlackbox(order) {
        order.blackbox_tax_category_a = order.getSpecificTax(21);
        order.blackbox_tax_category_b = order.getSpecificTax(12);
        order.blackbox_tax_category_c = order.getSpecificTax(6);
        order.blackbox_tax_category_d = order.getSpecificTax(0);
        return {
            'date': luxon.DateTime.now().toFormat("yyyyMMdd"),
            'ticket_time': luxon.DateTime.now().toFormat("HHmmss"),
            'insz_or_bis_number': this.config.module_pos_hr ? this.get_cashier().insz_or_bis_number : this.user.insz_or_bis_number,
            'ticket_number': order.sequence_number.toString(),
            'type': order.receipt_type ? order.receipt_type : order.get_total_with_tax() >= 0 ? 'NS' : 'NR',
            'receipt_total': Math.abs(order.get_total_with_tax()).toFixed(2).toString().replace(".", ""),
            'vat1': order.blackbox_tax_category_a ? Math.abs(order.blackbox_tax_category_a).toFixed(2).replace(".", "") : "",
            'vat2': order.blackbox_tax_category_b ? Math.abs(order.blackbox_tax_category_b).toFixed(2).replace(".", "") : "",
            'vat3': order.blackbox_tax_category_c ? Math.abs(order.blackbox_tax_category_c).toFixed(2).replace(".", "") : "",
            'vat4': order.blackbox_tax_category_d ? Math.abs(order.blackbox_tax_category_d).toFixed(2).replace(".", "") : "",
            'plu': order.getPlu(),
            'clock': order.clock ? order.clock : false,
        }
    },
    async pushDataToBlackbox(data) {
        const fdm = this.hardwareProxy.deviceControllers.fiscal_data_module;
        return new Promise(async (resolve, reject) => {
            fdm.addListener(data => data.status.status === "connected" ? resolve(data) : reject(data));
            await fdm.action({
                action: 'registerReceipt',
                high_level_message: data,
            });
        });
    },
    setDataForPushOrderFromBlackbox(order, data) {
        order.receipt_type = order.receipt_type ? order.receipt_type : (order.get_total_with_tax() >= 0 ? "NS" : "NR");
        order.blackbox_signature = data.value.signature;
        order.blackbox_unit_id = data.value.vsc;
        order.blackbox_plu_hash = order.getPlu();
        order.blackbox_vsc_identification_number = data.value.vsc;
        order.blackbox_unique_fdm_production_number = data.value.fdm_number;
        order.blackbox_ticket_counter = data.value.ticket_counter;
        order.blackbox_total_ticket_counter = data.value.total_ticket_counter;
        order.blackbox_ticket_counters = order.receipt_type + " " + data.value.ticket_counter + "/" + data.value.total_ticket_counter;
        order.blackbox_time = data.value.time.replace(/(\d{2})(\d{2})(\d{2})/g, '$1:$2:$3');
        order.blackbox_date = data.value.date.replace(/(\d{4})(\d{2})(\d{2})/g, '$3-$2-$1');
    },
    async _syncTableOrdersToServer() {
        if (this.useBlackBoxBe()) {
            for (const order of this.ordersToUpdateSet) {
                await this.pushProFormaOrder(order);
            }
        }
        super._syncTableOrdersToServer();
    },
    cashierHasPriceControlRights() {
        if (this.useBlackBoxBe()) {
            return false;
        } else {
            return super.cashierHasPriceControlRights();
        }
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.useBlackBoxBe = this.useBlackBoxBe();
        result.posIdentifier = this.config.name;
        if (order && this.useBlackBoxBe()) {
            result.receipt_type = order.receipt_type;
            result.blackboxDate = order.blackbox_date;
        }
        return result;
    }
});

patch(Order.prototype, {
    getSpecificTax(amount) {
        const tax = this.get_tax_details().find(tax => tax.tax.amount === amount);
        return tax ? tax.amount : false;
    },
    add_product(product, options) {
        if (this.pos.useBlackBoxBe() && product.get_price() < 0) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("It's forbidden to sell product with negative price when using the black box.\nPerform a refund instead."),
            });
            return;
        } else if (this.pos.useBlackBoxBe() && product.taxes_id.length === 0) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("Product has no tax associated with it."),
            });
            return;
        } else if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked() && product !== this.pos.workInProduct && !options.force) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("User must be clocked in."),
            });
            return;
        } else if (this.pos.useBlackBoxBe() && !this.pos.taxes_by_id[product.taxes_id[0]].identification_letter) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("Product has an invalid tax amount. Only 21%, 12%, 6% and 0% are allowed."),
            });
            return;
        } else if (this.pos.useBlackBoxBe() && product.id === this.pos.workInProduct.id && !options.force) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("This product is not allowed to be sold"),
            });
            return;
        } else if (this.pos.useBlackBoxBe() && product.id === this.pos.workOutProduct.id && !options.force) {
            this.pos.env.services.popup.add(ErrorPopup, {
                'title': _t("POS error"),
                'body': _t("This product is not allowed to be sold"),
            });
            return;
        }
        return super.add_product(product, options);
    },
    wait_for_push_order() {
        const result = super.wait_for_push_order();
        return Boolean(this.pos.useBlackBoxBe() || result);
    },
    export_as_JSON() {
        const json = super.export_as_JSON();

        if (!this.pos.useBlackBoxBe())
            return json;

            json.receipt_type = this.receipt_type;
            json.blackbox_unit_id = this.blackbox_unit_id,
            json.blackbox_pos_receipt_time = this.blackbox_pos_receipt_time,
            json.blackbox_ticket_counter = this.blackbox_ticket_counter,
            json.blackbox_total_ticket_counter = this.blackbox_total_ticket_counter,
            json.blackbox_ticket_counters = this.blackbox_ticket_counters,
            json.blackbox_signature = this.blackbox_signature,
            json.blackbox_tax_category_a = this.blackbox_tax_category_a,
            json.blackbox_tax_category_b = this.blackbox_tax_category_b,
            json.blackbox_tax_category_c = this.blackbox_tax_category_c,
            json.blackbox_tax_category_d = this.blackbox_tax_category_d,
            json.blackbox_date = this.blackbox_date,
            json.blackbox_time = this.blackbox_time,
            json.blackbox_unique_fdm_production_number = this.blackbox_unique_fdm_production_number,
            json.blackbox_vsc_identification_number = this.blackbox_vsc_identification_number,
            json.blackbox_plu_hash = this.getPlu(),
            json.blackbox_pos_version = this.pos.version.server_serie

        return json;
    },
    getPlu() {
        let order_str = "";
        this.get_orderlines().forEach(line => order_str += line.generatePluLine());
        const sha1 = Sha1.hash(order_str);
        return sha1.slice(sha1.length - 8);
    },
    export_for_printing() {
        let result = super.export_for_printing(...arguments);
        result.useBlackboxBe = Boolean(this.pos.useBlackBoxBe());
        if (this.pos.useBlackBoxBe()) {
            const order = this.pos.get_order();
            result.orderlines = result.orderlines.map((l) => ({
                ...l,
                price: l.price === "free" ? l.price : l.price + " " + l.taxLetter,
            }));
            result.tax_details = result.tax_details.map((t) => ({
                ...t,
                tax: { ...t.tax, letter: t.tax.identification_letter },
            }));
            result.blackboxBeData = {
                "pluHash": order.blackbox_plu_hash,
                "receipt_type": order.receipt_type,
                "terminalId": this.pos.config.id,
                "blackboxDate": order.blackbox_date,
                "blackboxTime": order.blackbox_time,

                "blackboxSignature": order.blackbox_signature,
                "versionId": this.pos.version.server_version,

                "vscIdentificationNumber": order.blackbox_vsc_identification_number,
                "blackboxFdmNumber": order.blackbox_unique_fdm_production_number,
                "blackbox_ticket_counter": order.blackbox_ticket_counter,
                "blackbox_total_ticket_counter": order.blackbox_total_ticket_counter,
                "ticketCounter": order.blackbox_ticket_counters,
                "fdmIdentifier": order.pos.config.certified_blackbox_identifier
            }
        }
        return result;
    },
});

patch(Orderline.prototype, {
    can_be_merged_with(orderline) {
        // The Blackbox doesn't allow lines with a quantity of 5 numbers.
        if (!this.pos.useBlackBoxBe() || (this.pos.useBlackBoxBe() && this.get_quantity() < 9999)) {
            return super.can_be_merged_with(orderline);
        }
        return false;
    },
    _generateTranslationTable() {
        let replacements = [
            ["ÄÅÂÁÀâäáàã", "A"],
            ["Ææ", "AE"],
            ["ß", "SS"],
            ["çÇ", "C"],
            ["ÎÏÍÌïîìí", "I"],
            ["€", "E"],
            ["ÊËÉÈêëéè", "E"],
            ["ÛÜÚÙüûúù", "U"],
            ["ÔÖÓÒöôóò", "O"],
            ["Œœ", "OE"],
            ["ñÑ", "N"],
            ["ýÝÿ", "Y"]
        ];

        const lowercaseAsciiStart = "a".charCodeAt(0);
        const lowercaseAsciiEnd = "z".charCodeAt(0);


        for (let lowercaseAsciiCode = lowercaseAsciiStart; lowercaseAsciiCode <= lowercaseAsciiEnd; lowercaseAsciiCode++) {
            const lowercaseChar = String.fromCharCode(lowercaseAsciiCode);
            const uppercaseChar = lowercaseChar.toUpperCase();
            replacements.push([lowercaseChar, uppercaseChar]);
        }

        let lookupTable = {};

        for (let i = 0; i < replacements.length; i++) {
            const letterGroup = replacements[i];
            const specialChars = letterGroup[0];
            const uppercaseReplacement = letterGroup[1];

            for (let j = 0; j < specialChars.length; j++) {
                const specialChar = specialChars[j];
                lookupTable[specialChar] = uppercaseReplacement;
            }
        }

        return lookupTable;
    },
    generatePluLine() {
        // |--------+-------------+-------+-----|
        // | AMOUNT | DESCRIPTION | PRICE | VAT |
        // |      4 |          20 |     8 |   1 |
        // |--------+-------------+-------+-----|

        // steps:
        // 1. replace all chars
        // 2. filter out forbidden chars
        // 3. build PLU line

        let amount = this._getAmountForPlu();
        let description = this.get_product().display_name;
        let price_in_eurocent = this.get_display_price() * 100;
        const vat_letter = this.getLineTaxLetter();

        amount = this._prepareNumberForPlu(amount, 4);
        description = this._prepareDescriptionForPlu(description);
        price_in_eurocent = this._prepareNumberForPlu(price_in_eurocent, 8);

        return amount + description + price_in_eurocent + vat_letter;
    },
    _prepareNumberForPlu(number, field_length) {
        number = Math.abs(number);
        number = Math.round(number);

        let number_string = number.toFixed(0);

        number_string = this._replaceHashAndSignChars(number_string);
        number_string = this._filterAllowedHashAndSignChars(number_string);

        // get the required amount of least significant characters
        number_string = number_string.substr(-field_length);

        // pad left with 0 to required size
        while (number_string.length < field_length) {
            number_string = "0" + number_string;
        }

        return number_string;
    },
    _prepareDescriptionForPlu(description) {
        description = this._replaceHashAndSignChars(description);
        description = this._filterAllowedHashAndSignChars(description);

        // get the 20 most significant characters
        description = description.substr(0, 20);

        // pad right with SPACE to required size of 20
        while (description.length < 20) {
            description = description + " ";
        }

        return description;
    },
    _getAmountForPlu() {
        let amount = this.get_quantity();
        const uom = this.get_unit();

        if (uom.is_unit) {
            return amount;
        } else {
            if (uom.category_id[1] === "Weight") {
                let uom_gram = null;
                for (let i = 0; i < this.pos.units_by_id.length; i++) {
                    const unit = this.pos.units_by_id[i];
                    if (unit.category_id[1] === "Weight" && unit.name === "g") {
                        uom_gram = unit;
                        break;
                    }
                }
                if (uom_gram) {
                    amount = (amount / uom.factor) * uom_gram.factor;
                }
            } else if (uom.category_id[1] === "Volume") {
                let uom_milliliter = null;
                for (let i = 0; i < this.pos.units_by_id.length; i++) {
                    const unit = this.pos.units_by_id[i];
                    if (unit.category_id[1] === "Volume" && unit.name === "Milliliter(s)") {
                        uom_milliliter = unit;
                        break;
                    }
                }
                if (uom_milliliter) {
                    amount = (amount / uom.factor) * uom_milliliter.factor;
                }
            }

            return amount;
        }
    },
    _replaceHashAndSignChars(str) {
        if (typeof str !== 'string') {
            throw "Can only handle strings";
        }

        let translationTable = this._generateTranslationTable();

        let replaced_char_array = str.split('').map((char) => {
            const translation = translationTable[char];
            return translation !== undefined ? translation : char;
        });

        return replaced_char_array.join("");
    },
    // for hash and sign the allowed range for DATA is:
    //   - A-Z
    //   - 0-9
    // and SPACE as well. We filter SPACE out here though, because
    // SPACE will only be used in DATA of hash and sign as description
    // padding
    _filterAllowedHashAndSignChars(str) {
        if (typeof str !== 'string') {
            throw "Can only handle strings";
        }

        let filtered_char_array = str.split('').filter(char => {
            const ascii_code = char.charCodeAt(0);

            if ((ascii_code >= "A".charCodeAt(0) && ascii_code <= "Z".charCodeAt(0)) ||
                (ascii_code >= "0".charCodeAt(0) && ascii_code <= "9".charCodeAt(0))) {
                return true;
            } else {
                return false;
            }
        });

        return filtered_char_array.join("");
    },
    export_as_JSON() {
        const json = super.export_as_JSON();

        if (this.pos.useBlackBoxBe()) {
            json.vat_letter = this.getLineTaxLetter();
        }

        return json;
    },
    getDisplayData() {
        if (!this.pos.useBlackBoxBe()) {
            return super.getDisplayData();
        }
        return {
            ...super.getDisplayData(),
            taxLetter: this.getLineTaxLetter(),
        };
    },
    getLineTaxLetter() {
        return this.pos.taxes_by_id[this.product.taxes_id[0]]?.identification_letter;
    },
});
