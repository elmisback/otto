jQuery(document).ready(function($){

    $('#createCourseModal, #joinCourseModal').on('shown.bs.modal', function(){
        $('input[name="course_title"]', this).focus();
        $('input[name="course_id"]', this).focus();
    });

    $('#deleteCourseModal, #leaveCourseModal').on('show.bs.modal', function(e){
        var target = $(e.relatedTarget);
        var targetRow = target.closest('.row');
        $('.course-title', this).text(targetRow.find('.attr-course-name').text());
        $('input[name="course_id"]', this).val(targetRow.find('.attr-course-id div').text());
    });

    $('#createCourseModal form, #joinCourseModal form').submit(function(){
        var form = $(this);
        $('input[name="ajax"]', form).val(true);
        var formData = form.serialize();
        var actionButton = form.find('input[type="submit"]');
        actionButton.button('loading');
        var response = $.post('/courses', formData).done(function(response){
            var data = $.parseJSON(response);
            if (data.success) {
                var newRow = $('.course-list .course').eq(0).clone(true).removeClass('course-none').attr('id', 'course-' + data.course_id).hide();
                $('.attr-course-id', newRow).html('<div>' + data.course_id + '</div>');
                $('.attr-course-name', newRow).html('<a href="' + data.course_url + '" title="' + data.course_title + '">' + data.course_title + '</a>');
                $('.attr-course-instructor', newRow).text(data.course_instructors);
                $('.attr-course-status', newRow).text(data.course_status);
                $('.attr-course-assignments', newRow).text(data.course_assignments);
                $('.attr-course-enrolled, .attr-course-pending', newRow).text('0');
                $('.course-none').before(newRow);
                newRow.slideToggle(300);
                $('input[name="course_title"]', form).val('');
                $('input[name="course_id"]', form).val('');
                $('.alert', form).remove();
                actionButton.button('reset');
                form.closest('.modal').modal('hide');
            } else {
                var alert = $('.modal-body .alert', form);
                if (alert.length > 0) {
                    alert.text(data.message);
                } else {
                    $('.modal-body', form).append('<div class="alert alert-danger" role="alert">' + data.message + '</div>').show();
                }
            }
        });
        return false;
    });

    $('#deleteCourseModal form, #leaveCourseModal form').submit(function(){
        var form = $(this);
        $('input[name="ajax"]', form).val(true);
        var formData = form.serialize();
        var actionButton = form.find('input[type="submit"]');
        actionButton.button('loading');
        var response = $.post('/courses', formData).done(function(response){
            var target = $('input[name="course_id"]', form).val();
            $('#course-' + target).slideToggle(300, function(){
                $(this).remove();
            });
            actionButton.button('reset');
            form.closest('.modal').modal('hide');
        });
        return false;
    });

});