function handleDayToggle(toggleElement) {
    const dayCard = $(toggleElement).closest('.day-card');
    const dayIndex = dayCard.find('[data-day-index]').data('day-index');
    const isClosed = $(toggleElement).is(':checked');
    const content = dayCard.find('.day-content');
    const statusBadge = $(`#status-badge-${dayIndex}`);
    const timeInputs = content.find('.time-input');
    
    // Update status badge
    statusBadge.removeClass('bg-success bg-danger')
              .addClass(isClosed ? 'bg-danger' : 'bg-success')
              .text(isClosed ? 'Tutup' : 'Buka');
    
    // Toggle waktu input
    timeInputs.prop('disabled', isClosed);
    if (isClosed) {
        timeInputs.removeAttr('required');
    } else {
        timeInputs.attr('required', 'required');
    }
    
    // Toggle tampilan konten
    if (isClosed) {
        content.slideUp(200);
    } else {
        content.slideDown(200);
    }
}

$(document).ready(function() {
    // Inisialisasi tooltip
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Handle day toggle change
    $('.day-toggle').change(function() {
        handleDayToggle(this);
    });
    
    // Inisialisasi status awal
    $('.day-toggle').each(function() {
        if ($(this).is(':checked')) {
            handleDayToggle(this);
        }
    });
    
    // Salin jadwal ke semua hari
    $('#copyWeekBtn').click(function() {
        if (confirm('Apakah Anda yakin ingin menyalin jadwal ini ke semua hari?')) {
            const sourceDay = $('.day-card').first();
            const isClosed = sourceDay.find('.day-toggle').is(':checked');
            const openTime = sourceDay.find('input[name$="-open_time"]').val();
            const closeTime = sourceDay.find('input[name$="-close_time"]').val();
            
            $('.day-card').each(function(index) {
                if (index > 0) {  // Skip the first day (source)
                    const toggle = $(this).find('.day-toggle');
                    const content = $(this).find('.day-content');
                    const timeInputs = content.find('.time-input');
                    
                    // Update toggle state
                    toggle.prop('checked', isClosed);
                    
                    // Update time inputs
                    if (!isClosed) {
                        content.find('input[name$="-open_time"]').val(openTime);
                        content.find('input[name$="-close_time"]').val(closeTime);
                    }
                    
                    // Update UI
                    handleDayToggle(toggle);
                }
            });
            
            // Show success message
            alert('Jadwal berhasil disalin ke semua hari');
        }
    });
    
    // Validasi form sebelum submit
    $('#operationalHoursForm').on('submit', function(e) {
        let isValid = true;
        const invalidDays = [];
        
        // Validasi setiap hari
        $('.day-card').each(function() {
            const dayCard = $(this);
            const dayName = dayCard.find('.form-check-label').text().trim();
            const isClosed = dayCard.find('.day-toggle').is(':checked');
            const timeSlots = dayCard.find('.time-slot');
            
            // Reset status validasi
            dayCard.removeClass('border-danger');
            
            // Jika hari buka, pastikan ada setidaknya satu slot waktu
            if (!isClosed) {
                if (timeSlots.length === 0) {
                    invalidDays.push(dayName);
                    dayCard.addClass('border-danger');
                    isValid = false;
                }
                
                // Validasi waktu buka dan tutup
                timeSlots.each(function() {
                    const openTime = $(this).find('input[name$="-open_time"]').val();
                    const closeTime = $(this).find('input[name$="-close_time"]').val();
                    
                    if (!openTime || !closeTime) {
                        invalidDays.push(dayName);
                        $(this).addClass('border-danger');
                        isValid = false;
                    } else if (openTime >= closeTime) {
                        invalidDays.push(dayName);
                        $(this).addClass('border-danger');
                        isValid = false;
                    }
                });
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            
            // Buat daftar hari yang tidak valid
            const uniqueDays = [...new Set(invalidDays)];
            const errorMessage = `Mohon periksa jadwal untuk hari: ${uniqueDays.join(', ')}. Pastikan waktu buka lebih awal dari waktu tutup.`;
            
            // Tampilkan pesan error
            const errorHtml = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <div>${errorMessage}</div>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>`;
                
            // Hapus alert error sebelumnya jika ada
            $('.alert.alert-danger').remove();
            
            // Tambahkan alert error baru
            $('.form-section').prepend(errorHtml);
            
            // Scroll ke atas form
            $('html, body').animate({
                scrollTop: $('.form-section').offset().top - 20
            }, 500);
        }
    });
});
