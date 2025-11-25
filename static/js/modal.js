/**
 * 弹窗管理模块
 *
 * 提供弹窗的打开、关闭等操作
 */

(function (window) {
    'use strict';

    const APP = window.APP || {};

    /**
     * 打开弹窗
     *
     * :param {string} rootId: 弹窗根节点ID
     * :returns: 无
     * :rtype: void
     */
    function openModalById(rootId) {
        const root = document.getElementById(rootId);
        if (!root) return;
        root.style.display = 'flex';
        root.setAttribute('aria-hidden', 'false');
    }

    /**
     * 关闭弹窗
     *
     * :param {string} rootId: 弹窗根节点ID
     * :returns: 无
     * :rtype: void
     */
    function closeModalById(rootId) {
        const root = document.getElementById(rootId);
        if (!root) return;
        root.style.display = 'none';
        root.setAttribute('aria-hidden', 'true');
    }

    /**
     * 关闭所有弹窗
     *
     * :returns: 无
     * :rtype: void
     */
    function closeAllModals() {
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            if (backdrop.style.display === 'flex' || backdrop.getAttribute('aria-hidden') === 'false') {
                backdrop.style.display = 'none';
                backdrop.setAttribute('aria-hidden', 'true');
            }
        });
    }

    // 导出到全局
    APP.modal = {
        open: openModalById,
        close: closeModalById,
        closeAll: closeAllModals
    };

    window.APP = APP;

})(window);

