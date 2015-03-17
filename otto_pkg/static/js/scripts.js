jQuery(document).ready(function($){

    $(document).on('click', 'a', function(e){
        e.preventDefault();
        var response = $.ajax({
            url: $(this).attr('href')
        }).done(function(response){
            $('.view-container').replaceWith(response);
            history.pushState({}, '', $(this).attr('href'));
        });
        return false;
    });

    $(document).on('shown.bs.modal', '#addCourseModal', function(){
        $('input[name="course_title"]', this).focus();
        $('input[name="course_id"]', this).focus();
    });

    $(document).on('show.bs.modal', '#removeCourseModal', function(e){
        var target = $(e.relatedTarget);
        var targetRow = target.closest('.course');
        var courseName = $('.course-name', targetRow);
        var courseID = $('.course-id div', targetRow);
        $('.course-title', this).text($.trim(courseName.text()));
        $('input[name="course_id"]', this).val(courseID.text());
        $('form', this).attr('action', targetRow.attr('data-action'));
    });

    $(document).on('hidden.bs.modal', '#addCourseModal', function(){
        $('.alert', this).remove();
        $('input[name="course_title"]', this).val('');
        $('input[name="course_id"]', this).val('');
    });

    $(document).on('submit', '#addCourseModal form', function(){
        var form = $(this);
        var formData = form.serialize();
        var actionButton = $('button[type="submit"]', form);
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var data = $.parseJSON(response);
            var newRow = $('.course-list .course').eq(0).clone(true).removeClass('course-none').attr('id', 'course-' + data.id).attr('data-action', data.course_url).hide();
            $('.course-none-message', newRow).remove();
            $('.course-id', newRow).html('<div>' + data.id + '</div>');
            $('.course-name', newRow).html('<a href="' + data.assignments_url + '" title="' + data.title + ' - Assignments">' + data.title + '</a>');
            $('.course-assignments-url', newRow).attr('href', data.assignments_url);
            $('.course-students-url', newRow).attr('href', data.students_url);
            $('.course-list').append(newRow);
            newRow.slideToggle(300);
            form.closest('.modal').modal('hide');
        }).fail(function(response){
            var data = $.parseJSON(response.responseText);
            var alert = $('.modal-body .alert', form);
            if (alert.length > 0) {
                alert.text(data.message);
            } else {
                $('.modal-body', form).append('<div class="alert alert-danger" role="alert">' + data.message + '</div>').show();
            }
            $('input[name="course_title"]', form).focus();
            $('input[name="course_id"]', form).focus();
        });
        actionButton.button('reset');
        return false;
    });

    $(document).on('submit', '#removeCourseModal form', function(){
        var form = $(this);
        var formData = form.serialize();
        var actionButton = $('button[type="submit"]', form);
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var target = $('input[name="course_id"]', form).val();
            $('#course-' + target).slideToggle(300, function(){
                $(this).remove();
            });
            form.closest('.modal').modal('hide');
        });
        actionButton.button('reset');
        return false;
    });

    $(document).on('submit', '.approve-student-form, .unapprove-student-form, .approve-students-form', function(){
        var form = $(this);
        var formData = form.serialize();
        var actionButton = $('button[type="submit"]', form);
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var targetRow = form.closest('.student');
            if (targetRow.hasClass('student-approved')) {
                targetRow.removeClass('student-approved').addClass('student-unapproved list-group-item-warning');
            } else {
                targetRow.removeClass('student-unapproved list-group-item-warning').addClass('student-approved');
            }
        });
        actionButton.button('reset');
        return false;
    })

});
