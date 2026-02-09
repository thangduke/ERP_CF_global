/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class StockDashboard extends Component {
    static template = "warehouse_pro.StockDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.debounceTimeout = null;
        const warehouseColumns = {
            store_id: { label: "Kho", visible: false },
            shelf_id: { label: "Kệ", visible: false },
            shelf_level_id: { label: "Khoang", visible: false },

            name: { label: "Mtr#", visible: true },
            mtr_type: { label: "Mtr Type", visible: true },
            mtr_code: { label: "Mtr Code", visible: true },

            rate: { label: "Unit", visible: true },
            dimension: { label: "Dimension", visible: true },
            color_item: { label: "Color#", visible: true },
            color_name: { label: "Color Name", visible: true },
            supplier: { label: "Supplier", visible: true },
            price: { label: "Price $", visible: true },

            qty_open: { label: "SL Tồn đầu", visible: true },
            value_open: { label: "Dư đầu", visible: false },

            qty_in: { label: "SL Nhập", visible: true },
            value_in: { label: "Tiền Nhập", visible: false },

            qty_out: { label: "SL Xuất", visible: true },
            value_out: { label: "Tiền Xuất", visible: false },

            qty_close: { label: "SL Tồn cuối", visible: true },
            value_close: { label: "Dư cuối", visible: false },
        };

        const programColumns = {
            order_id: { label: "Chương trình", visible: false },
            material_id: { label: "Vật tư", visible: false },
            name: { label: "Mtr#", visible: true },
            mtr_type: { label: "Mtr Type", visible: true },
            mtr_code: { label: "Mtr Code", visible: true },
            rate: { label: "Unit", visible: true },
            dimension: { label: "Dimension", visible: true },
            color_item: { label: "Color#", visible: true },
            color_name: { label: "Color Name", visible: true },
            supplier: { label: "Supplier", visible: true },
            price: { label: "Price $", visible: true },

            qty_open: { label: "SL Tồn đầu", visible: true },
            value_open: { label: "Dư đầu", visible: false },

            qty_in: { label: "SL Nhập", visible: true },
            value_in: { label: "Tiền Nhập", visible: false },

            qty_out: { label: "SL Xuất", visible: true },
            value_out: { label: "Tiền Xuất", visible: false },

            qty_close: { label: "SL Tồn cuối", visible: true },
            value_close: { label: "Dư cuối", visible: false },
        };

        const xntColumns = {
            material_name: { label: "Mtr#", visible: true },
            material_code: { label: "Mtr_code", visible: true },
            mtr_type: { label: "Mtr Type", visible: true },
            material_unit: { label: "Unit", visible: true },
            dimension: { label: "Dimension", visible: true },
            color_item: { label: "Color#", visible: true },
            color_name: { label: "Color Name", visible: true },
            
            supplier: { label: "Supplier", visible: true },
            price: { label: "Price $", visible: true },
            
            opening_qty: { label: "SL Tồn đầu", visible: true },
            value_open: { label: "Dư đầu", visible: false },
            
            qty_in: { label: "SL Nhập", visible: true },
            value_in: { label: "Tiền Nhập", visible: false },
            
            qty_out: { label: "SL Xuất", visible: true },
            value_out: { label: "Tiền Xuất", visible: false },

            ending_qty: { label: "SL Tồn cuối", visible: true },
            value_close: { label: "Dư cuối", visible: false },
        };

        this.state = useState({
            page: "page1", // 'page1' for Warehouse, 'page2' for Program, 'page3' for XNT
            kpis: {},
            stock_list: [],
            order_list: [],
            xnt_report_lines: [],
            filter_store_id: "",
            filter_order_id: "",
            filter_shelf_id: "",
            filter_shelf_level_id: "",
            filter_start_date: "",
            filter_end_date: "",
            available_stores: [],
            available_orders: [],
            available_shelves: [],
            available_shelf_levels: [],
            columns: warehouseColumns,
            stock_search_term: "",
            order_search_term: "",
            xnt_search_term: "",

        });
        this.warehouseColumns = warehouseColumns;
        this.programColumns = programColumns;
        this.xntColumns = xntColumns;

        onWillStart(async () => {
            await this.fetchAvailableStores();
            await this.fetchAvailableOrders();
            await this.fetchDashboardData();
        });

        onMounted(() => {
            // this.renderCharts();
        });
    }

    get filteredXntReportList() {
        const searchTerm = (this.state.xnt_search_term || "").toLowerCase();
        let lines = this.state.xnt_report_lines;

        // Sort by mtr_type
        lines.sort((a, b) => {
            const typeA = a.mtr_type || '';
            const typeB = b.mtr_type || '';
            return typeA.localeCompare(typeB);
        });

        if (!searchTerm) {
            return lines;
        }

        return lines.filter(line => {
            return (line.material_name && line.material_name.toLowerCase().includes(searchTerm)) ||
                   (line.material_code && line.material_code.toLowerCase().includes(searchTerm)) ||
                   (line.mtr_type && line.mtr_type.toLowerCase().includes(searchTerm)) ||
                   (line.supplier && line.supplier.toLowerCase().includes(searchTerm));
        });
    }

    get filteredOrderList() {
        const searchTerm = (this.state.order_search_term || "").toLowerCase();
        let orders = this.state.order_list;

        orders.sort((a, b) => {
            const typeA = a.mtr_type || '';
            const typeB = b.mtr_type || '';
            return typeA.localeCompare(typeB);
        });

        if (!searchTerm) {
            return orders;
        }
        return orders.filter(order => {
            return (order.name && order.name.toLowerCase().includes(searchTerm)) ||
                   (order.mtr_type && order.mtr_type.toLowerCase().includes(searchTerm)) ||
                   (order.mtr_code && order.mtr_code.toLowerCase().includes(searchTerm)) ||
                   (order.supplier && order.supplier.toLowerCase().includes(searchTerm));
        });
    }

    get filteredStockList() {
        const searchTerm = (this.state.stock_search_term || "").toLowerCase();
        let stocks = this.state.stock_list;

        stocks.sort((a, b) => {
            const typeA = a.mtr_type || '';
            const typeB = b.mtr_type || '';
            return typeA.localeCompare(typeB);
        });

        if (!searchTerm) {
            return stocks;
        }
        return stocks.filter(stock => {
            return (stock.name && stock.name.toLowerCase().includes(searchTerm)) ||
                   (stock.mtr_type && stock.mtr_type.toLowerCase().includes(searchTerm)) ||
                   (stock.mtr_code && stock.mtr_code.toLowerCase().includes(searchTerm)) ||
                   (stock.supplier && stock.supplier.toLowerCase().includes(searchTerm));
        });
    }

    get tableHeaders() {
        return Object.entries(this.state.columns)
            .filter(([, value]) => value.visible)
            .map(([key, value]) => ({ key, label: value.label }));
    }

    toggleColumn = (columnKey) => {
        this.state.columns[columnKey].visible = !this.state.columns[columnKey].visible;
    }
    // === Load danh sách chương trình ===
    async fetchAvailableOrders() {
        try {
            this.state.available_orders = await this.orm.call(
                "warehouse.order",
                "search_read",
                [[], ["id", "name"]]
            );
        } catch (error) {
            console.error("Lỗi khi load danh sách chương trình:", error);
        }
    }

    // === Load danh sách kho ===
    async fetchAvailableStores() {
        try {
            this.state.available_stores = await this.orm.call(
                "store.list",
                "search_read",
                [[], ["id", "name"]]
            );
        } catch (error) {
            console.error("Lỗi khi load danh sách kho:", error);
        }
    }

    async fetchAvailableShelves() {
        try {
            const domain = this.state.filter_store_id ? [['store_id', '=', parseInt(this.state.filter_store_id, 10)]] : [];
            this.state.available_shelves = await this.orm.call(
                "shelf.list",
                "search_read",
                [domain, ["id", "name"]]
            );
        } catch (error) {
            console.error("Lỗi khi load danh sách kệ:", error);
        }
    }

    async fetchAvailableShelfLevels() {
        try {
            const domain = this.state.filter_shelf_id ? [['shelf_id', '=', parseInt(this.state.filter_shelf_id, 10)]] : [];
            this.state.available_shelf_levels = await this.orm.call(
                "shelf.level",
                "search_read",
                [domain, ["id", "name"]]
            );
        } catch (error) {
            console.error("Lỗi khi load danh sách khoang:", error);
        }
    }


    // === Load dữ liệu chính của dashboard ===
    async fetchDashboardData() {
        const filters = {
            page: this.state.page,
            filter_order_id: this.state.filter_order_id,
            filter_store_id: this.state.filter_store_id,
            filter_shelf_id: this.state.filter_shelf_id,
            filter_shelf_level_id: this.state.filter_shelf_level_id,
            start_date: this.state.filter_start_date,
            end_date: this.state.filter_end_date,
        };

        try {
            const data = await this.orm.call("warehouse.dashboard", "get_dashboard_data", [filters]);
            this.state.kpis = data.kpis || {};
            if (this.state.page === 'page1') {
                this.state.stock_list = data.stock_list || [];
                this.state.order_list = [];
                this.state.xnt_report_lines = [];
            } else if (this.state.page === 'page2') {
                this.state.order_list = data.order_list || [];
                this.state.stock_list = [];
                this.state.xnt_report_lines = [];
            } else if (this.state.page === 'page3') {
                this.state.xnt_report_lines = data.lines || [];
                this.state.stock_list = [];
                this.state.order_list = [];
            }
        } catch (error) {
            console.error("Lỗi khi load dữ liệu dashboard:", error);
        }
    }

        // === Chuyển trang ===
    switchPage = (page) => {
        if (this.state.page !== page) {
            this.state.page = page;
            if (page === 'page1') {
                this.state.columns = this.warehouseColumns;
                this.resetFilters(['filter_order_id', 'filter_start_date', 'filter_end_date']);
            } else if (page === 'page2') {
                this.state.columns = this.programColumns;
                this.resetFilters(['filter_store_id', 'filter_shelf_id', 'filter_shelf_level_id', 'filter_start_date', 'filter_end_date']);
            } else if (page === 'page3') {
                this.state.columns = this.xntColumns;
                this.resetFilters(['filter_order_id', 'filter_shelf_id', 'filter_shelf_level_id']);
            }
            this.applyFilters();
        }
    }
    
    resetFilters(filterKeys) {
        for (const key of filterKeys) {
            this.state[key] = "";
        }
        // Also reset search terms and dependent filters
        if (filterKeys.includes('filter_store_id')) {
            this.state.available_shelves = [];
            this.state.available_shelf_levels = [];
        }
        this.state.stock_search_term = "";
        this.state.order_search_term = "";
        this.state.xnt_search_term = "";
    }
    
    // === Áp dụng bộ lọc ===
    applyFilters = () => {
        clearTimeout(this.debounceTimeout);
        this.debounceTimeout = setTimeout(async () => {
            await this.fetchDashboardData();
        }, 500);
    }

    onStoreChange = async () => {
        this.state.filter_shelf_id = "";
        this.state.filter_shelf_level_id = "";
        this.state.available_shelves = [];
        this.state.available_shelf_levels = [];
        
        if (this.state.filter_store_id) {
            await this.fetchAvailableShelves();
        }
        
        this.applyFilters();
    }

    onShelfChange = async () => {
        this.state.filter_shelf_level_id = "";
        this.state.available_shelf_levels = [];

        if (this.state.filter_shelf_id) {
            await this.fetchAvailableShelfLevels();
        }

        this.applyFilters();
    }

    // === Mở thẻ kho ===
    openStockCard(material_id) {
        if (material_id) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Thẻ kho',
                res_model: 'material.stock.card',
                views: [[false, 'list'], [false, 'form']],
                domain: [['material_id', '=', material_id]],
                target: 'current',
            });
        }
    }

    openStockListRecord(recordId) {
        const resModel = this.state.page === 'page1' 
            ? 'material.stock.summary' 
            : 'material.stock.program.summary';
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: resModel,
            res_id: recordId,
            views: [[false, 'form']],
            target: 'new',
        });
    }
    exportXntReport() {
        const params = {};
        if (this.state.filter_store_id) {
            params.store_id = this.state.filter_store_id;
        }
        if (this.state.filter_start_date) {
            params.start_date = this.state.filter_start_date;
        }
        if (this.state.filter_end_date) {
            params.end_date = this.state.filter_end_date;
        }
        const url = `/export/xnt_report?${new URLSearchParams(params).toString()}`;
        window.open(url, '_blank');
    }

    exportStockList(page) {
        if (page !== 'page1' && page !== 'page2') {
            return;
        }
        const model = page === 'page1' ? 'material.stock.summary' : 'material.stock.program.summary';
        
        const domain = [];
        if (page === 'page1') {
            if (this.state.filter_store_id) domain.push(['store_id', '=', parseInt(this.state.filter_store_id)]);
            if (this.state.filter_shelf_id) domain.push(['shelf_id', '=', parseInt(this.state.filter_shelf_id)]);
            if (this.state.filter_shelf_level_id) domain.push(['shelf_level_id', '=', parseInt(this.state.filter_shelf_level_id)]);
        } else { // page2 for program summary
            if (this.state.filter_order_id) domain.push(['program_id', '=', parseInt(this.state.filter_order_id)]);
        }

        let url;
        if (page === 'page1') {
            url = `/export/stock_summary?model=${model}&domain=${JSON.stringify(domain)}`;
        } else {
            // This is for the program summary page, assuming a different export route
            url = `/export/stock_program_summary?model=${model}&domain=${JSON.stringify(domain)}`;
        }
        
        window.open(url, '_blank');
    }
    
}

// Đăng ký action cho Odoo
registry.category("actions").add("stock_dashboard", StockDashboard);
export default StockDashboard;