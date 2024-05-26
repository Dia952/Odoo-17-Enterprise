/** @odoo-module **/
"use_strict";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('sale_subscription_tour', {
    url: "/web",
    sequence: 250,
    rainbowMan: true,
    rainbowManMessage: () => markup(_t("<b>Congratulations</b>, your first subscription quotation is ready to be sent!")),
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="sale_subscription.menu_sale_subscription_root"]',
	content: _t('Want recurring billing via subscription management? Get started by clicking here'),
    position: 'bottom',
},
{
    trigger: '.dropdown-toggle[data-menu-xmlid="sale_subscription.menu_sale_subscription"]',
    content: _t('Let\'s go to the catalog to create our first subscription product'),
    position: 'bottom',
},
{
    trigger: '.dropdown-item[data-menu-xmlid="sale_subscription.menu_sale_subscription_product"]',
    content: _t('Create your first subscription product here'),
    position: 'bottom',
},
{
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_renderer',
    content: _t('Go ahead and create a new product'),
    position: 'right',
},
{
    trigger: 'input.o_input[id="name"]', // remove after ?
    extra_trigger: '.o_form_editable',
    content: markup(_t('Choose a product name.<br/><i>(e.g. eLearning Access)</i>')),
    position: 'right',
    width: 200,
},
{
    trigger: 'a.nav-link[name="pricing"]',
    extra_trigger: '.o_form_editable',
    content: _t("Let's configure the product price"),
    position: 'right',
},
{
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: '.o_form_editable',
    content: _t("Let's add a pricing with a recurrence"),
    run: "click",
},
{
    trigger: '.dropdown-item[data-menu-xmlid="sale_subscription.menu_sale_subscription_root"]',
    content: _t('Go back to the subscription view'),
    position: 'bottom',
},
{
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_renderer',
    content: _t('Go ahead and create a new subscription'),
    position: 'right',
},
{
    trigger: '.o_field_widget[name="partner_id"]',
    content: _t('Assign a new partner to the contract'),
    position: 'right',
},
{
    trigger: ".o_field_x2many_list_row_add > a",
    content:  _t('Click here to add some products or services to your quotation.'),
    run: 'click',
},
{
    trigger: ".o_field_widget[name='product_id'], .o_field_widget[name='product_template_id']",
    extra_trigger: ".o_sale_order",
    content: _t("Select a recurring product"),
    position: "right",
},
{
    trigger: 'div.o_row',
    content:  _t("Select a recurrence"),
    position: "bottom",
},
{
    trigger: 'div[name="subscription_pill"]',
    content:  _t("Your contract is recurrent"),
    position: "bottom",
},

]});
