/**
 * 全局常量和配置
 *
 * 此文件由 home.html 模板初始化，包含所有需要Django模板标签渲染的URL常量
 * 其他JS模块通过 window.APP 访问这些常量
 */

// 初始化全局命名空间
window.APP = window.APP || {};

// 本地存储键名
window.APP.STORAGE_KEY = 'homeActiveNavKey';

// 图标URL
window.APP.ICONS = {
    EDIT: '/static/icons/edit.svg',
    CONFIRM: '/static/icons/confirm.svg',
    CANCEL: '/static/icons/cancel.svg',
    CLOSE: '/static/icons/close.svg'
};

// API URL（需要在 home.html 中通过 Django 模板标签注入）
window.APP.URLS = {};

