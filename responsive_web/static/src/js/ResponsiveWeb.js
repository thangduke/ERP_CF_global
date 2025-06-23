/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import SearchResult from './SearchResult';
const { fuzzyLookup } = require('@web/core/utils/search');
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";

/**
 * WebResponsive Component
 *
 * This component adds responsive search functionality within the Odoo web client.
 * It listens for key events and initiates a search when alphanumeric keys are pressed.
 * The search queries available applications and menu items and displays the matching results in a modal.
 */
class WebResponsive extends Component {
    /**
     * Initializes the component, sets up the state, services, and registers event listeners.
     */
    setup() {
        super.setup(...arguments);
        this.root = useRef('root');
        this.action = useService("action");
        this.menuService = useService('menu');
        this.search_input = useRef("search-input");
        this.state = useState({
            results: [],
            showModal: false,
            menus: [],
            should_replace_nav: false,
            query: "",
            currentIndex: 0, // Chỉ số ảnh hiện tại
            totalImages: 17, // Tổng số ảnh (image10.jpg đến image26.jpg)
        });
        this._search_def = new $.Deferred();
        let { apps, menuItems } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;
        this._searchableMenus = menuItems;

        // Bắt đầu slideshow khi component được gắn vào DOM
        onMounted(() => {
            this.startSlideshow();
        });

        // Dừng slideshow khi component bị gỡ khỏi DOM
        onWillUnmount(() => {
            this.stopSlideshow();
        });

        onWillStart(async () => {
            this.state.menus = await this.menuService.getApps();
            this.state.should_replace_nav = true;
        });
        window.addEventListener('keydown', this.onKeyDown.bind(this));
    }

    /**
     * Bắt đầu slideshow tự động chuyển ảnh sau mỗi 2 giây.
     */
    startSlideshow() {
        this.interval = setInterval(() => {
            this.nextImage();
        }, 2000); // Chuyển ảnh sau mỗi 2 giây
    }

    /**
     * Dừng slideshow khi không cần thiết.
     */
    stopSlideshow() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }

    /**
     * Chuyển sang ảnh tiếp theo.
     */
    nextImage() {
        this.state.currentIndex = (this.state.currentIndex + 1) % this.state.totalImages;
    }

    /**
     * Handles keydown events to trigger the search modal.
     *
     * @param {Event} event - The keydown event triggered by the user.
     */
    onKeyDown(event) {
        if (this.state.showModal) {
            return;
        }
        if (/^[a-zA-Z0-9]$/.test(event.key)) {
            this.state.query = `${this.state.query}${event.key}`;
            this._searchMenus();
            this.state.showModal = true;
            setTimeout(() => this.root.el?.querySelector(".SearchInput")?.focus(), 1000);
        }
    }

    /**
     * Closes the search modal, clears the search results and query.
     */
    closeModal() {
        this.state.showModal = false;
        this.state.results = [];
        this.state.query = "";
    }

    /**
     * Removes the keydown event listener when the component is unmounted.
     */
    willUnmount() {
        window.removeEventListener('keydown', this.onKeyDown.bind(this));
    }

    /**
     * Performs a search through the available apps and menu items using fuzzy matching.
     * Updates the search results in the component state.
     */
    _searchMenus() {
        var query = this.state.query;
        if (query === "") {
            return;
        }
        var results = [];
        // Search through apps
        fuzzyLookup(query, this._apps, (menu) => menu.label)
            .forEach((menu) => {
                results.push({
                    category: "apps",
                    name: menu.label,
                    actionID: menu.actionID,
                    id: menu.id,
                    webIconData: menu.webIconData,
                });
            });
        // Search through menu items
        fuzzyLookup(query, this._searchableMenus, (menu) =>
                (menu.parents + " / " + menu.label).split("/").reverse().join("/"))
            .forEach((menu) => {
                results.push({
                    category: "menu_items",
                    name: menu.parents + " / " + menu.label,
                    actionID: menu.actionID,
                    id: menu.id,
                });
            });
        this.state.results = results;
    }

    /**
     * Handles the input event to update the search query and trigger a new search.
     *
     * @param {Event} event - The input event from the search field.
     */
    onInput(event) {
        this.state.query = event.target.value;
        this._searchMenus();
    }
}

WebResponsive.template = 'responsive_web.WebResponsiveTmp';
WebResponsive.components = {
    ...WebResponsive.components,
    SearchResult
};
registry.category('actions').add('web_responsive', WebResponsive);