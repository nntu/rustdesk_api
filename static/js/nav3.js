/**
 * 用户管理页面模块 (nav-3)
 *
 * 处理用户列表、编辑、重置密码、删除、创建等功能
 */

(function (window) {
    'use strict';

    const APP = window.APP || {};

    // 延迟获取依赖，避免模块加载顺序问题
    function getConstants() {
        return {
            STORAGE_KEY: APP.STORAGE_KEY || 'homeActiveNavKey',
            URLS: APP.URLS || {}
        };
    }

    /**
     * 收集查询参数
     *
     * :param {HTMLFormElement} formEl: 表单元素
     * :returns: 查询参数对象
     * :rtype: Object
     */
    function collectQueryOptions(formEl) {
        const params = {};
        if (!formEl) return params;
        const formData = new FormData(formEl);
        const q = formData.get('q');
        if (q !== null && String(q).trim() !== '') {
            params.q = String(q).trim();
        }
        const pageSize = formData.get('page_size');
        if (pageSize !== null && String(pageSize).trim() !== '') {
            params.page_size = String(pageSize).trim();
        }
        return params;
    }

    // 导出到全局
    APP.nav3 = {
        collectQueryOptions
    };

    window.APP = APP;

})(window);
