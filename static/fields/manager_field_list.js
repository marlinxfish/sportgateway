// manager_field_list.js
// Script for manager field list page (tooltip, etc)
document.addEventListener('DOMContentLoaded', function() {
    // Inisialisasi tooltip
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
    // Tambahkan script lain terkait halaman ini di bawah sini
});
