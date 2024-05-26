/** @odoo-module */

const PAPER_TO_CSS = {
    margin_top: "padding-top",
    margin_left: "padding-left",
    margin_right: "padding-right",
    print_page_width: "width",
    print_page_height: "min-height",
};

export function getCssFromPaperFormat(paperFormat, unit = "mm") {
    return Object.entries(paperFormat)
        .map((f) => `${PAPER_TO_CSS[f[0]]}:${f[1]}${unit}`)
        .join(";");
}
