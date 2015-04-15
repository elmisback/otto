jQuery(document).ready(function($){

    function initDateTimePicker() {
        $('.datetimepicker').datetimepicker({
            format: 'MMMM DD, YYYY hh:mmA',
            widgetPositioning: {
                horizontal: 'left',
                vertical: 'bottom'
            }
        });
    }

    function updateViewport(response, url) {
        var viewWrapper = $('.view-container-wrapper');
        var oldView = $('.view-container');
        var newView = $(response);
        var oldViewBreadcrumb = $('.site-breadcrumb li', oldView);
        var newViewBreadcrumb = $('.site-breadcrumb li', newView);
        var oldViewDirection = oldViewBreadcrumb.length > newViewBreadcrumb.length ? 'fading-right' : 'fading-left';
        var newViewDirection = oldViewBreadcrumb.length > newViewBreadcrumb.length ? 'fading-left' : 'fading-right';
        newView.addClass('changing ' + newViewDirection);
        viewWrapper.append(newView);
        setTimeout(function(){
            newView.removeClass(newViewDirection);
        }, 150);
        viewWrapper.height(oldView.height());
        oldView.addClass('changing ' + oldViewDirection);
        newView.removeClass('changing');
        viewWrapper.height('auto');
        setTimeout(function(){
            oldView.remove();
        }, 300);
        history.replaceState({}, '', url);
        initDateTimePicker();
    }

    // handles the transition between pages
    $(document).on('click', 'a:not(.non-ajax)', function(e){
        e.preventDefault();
        var url = $(this).attr('href');
        // don't load the page if it's the same one
        if (url == window.location.href.replace(/^.*\/\/[^\/]+/, '')) {
            return;
        }
        var response = $.ajax({ url: url }).done(function(response){
            updateViewport(response, url)
        });
        return false;
    });

    // handles the uploading of new submissions on the 'assignment' view
    $(document).on('submit', '.modal-upload-submission form', function(){
        var form = $(this);
        var data = new FormData();
        var fileUpload = $('input[type="file"]');
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        actionButton.button('loading');
        $.each(fileUpload[0].files, function(key, value){
            data.append(key, value);
        });
        if (fileUpload[0].files.length <= 0) {
            $('.alert', form).remove();
            $('.modal-body', form).append('<div class="alert alert-danger">Please choose a file to upload as your submission.</div>');
            actionButton.button('reset');
            return false;
        }
        var response = $.ajax({
            method: 'POST',
            url: form.attr('action'),
            data: data,
            cache: false,
            contentType: false,
            processData: false
        }).done(function(response){
            var data = $.parseJSON(response);
            var url = form.attr('data-follow-up') + data + '/';
            $.post(url, form.serialize()).done(function(response){
                var data = $.parseJSON(response);
                console.log(data);
                $('.modal-upload-submission form').attr('action', data.upload_url);
                if (data.replaced_submission) {
                    var submission = $('#submission-' + data.replaced_submission);
                    submission.attr('id', 'submission-' + data.submission.id);
                    $('.download-url', submission).attr('href', data.submission.download_url);
                    $('.submission-filename', submission).text(data.submission.filename);
                    $('.submission-timestamp', submission).text(data.submission.timestamp);
                    $('.hidden', submission).removeClass('hidden');
                } else {
                    var submission = $('#submission-0');
                    submission.attr('id', 'submission-' + data.submission.id);
                    $('.no-submission-message', submission).remove();
                    $('.download-url', submission).attr('href', data.submission.download_url);
                    $('.submission-author', submission).text(data.submission.author);
                    $('.submission-filename', submission).text(data.submission.filename);
                    $('.submission-timestamp', submission).text(data.submission.timestamp);
                    $('.hidden', submission).removeClass('hidden');
                }
                actionButton.button('reset');
                form.closest('.modal').modal('hide');
            }).fail(function(response){
                var data = $.parseJSON(response.responseText);
                $('.alert', form).remove();
                if (data.message) {
                    $('.modal-body', form).append('<div class="alert alert-danger">' + data.message + '</div>');
                }
                actionButton.button('reset');
            });
        }).fail(function(response){
            $('.alert', form).remove();
            $('.modal-body', form).append('<div class="alert alert-danger">There was a problem uploading your submission. Your filesize may be too large. Please try again.</div>');
            actionButton.button('loading');
        });
        return false;
    });

    // handles the submission of new comments in the 'assignment' view
    $(document).on('submit', '.comment-form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var data = $.parseJSON(response);
            var newComment = $('#comment-0').clone(true);
            newComment.hide().attr('id', 'comment-' + data.id);
            $('.comment-author', newComment).text(data.author);
            $('.comment-timestamp', newComment).text(data.timestamp);
            $('.comment-message', newComment).text(data.message);
            $('input[name="comment_id"]', newComment).val(data.id);
            if (data.is_instructor) {
                $('.comment-author', newComment).addClass('text-primary');
            }
            $('.comment-form').before(newComment);
            newComment.fadeIn(300);
            form.find('textarea[name="comment_message"]').val('');
            $('.alert', form).remove();
            actionButton.button('reset');
        }).fail(function(response){
            var data = $.parseJSON(response.responseText);
            $('.alert', form).remove();
            for (i = 0; i < data.failed_inputs.length; i++) {
                var input = $('textarea[name="' + data.failed_inputs[i][0] + '"]', form);
                input.parent().append('<div class="alert alert-danger" role="alert">' + data.failed_inputs[i][1] + '</div>');
            }
            actionButton.button('reset');
        });
        return false;
    });

    // handles the deletion of comments in the 'assignment' view
    $(document).on('submit', '.delete-comment-form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        var response = $.post(form.attr('action'), formData).done(function(response){
            form.closest('.comment').fadeOut(300, function(){
                $(this).remove();
            });
        });
        return false;
    });

    // handles the submission of assignment edit form changes
    $(document).on('submit', '.assignment_edit_form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
                updateViewport(response, window.location.href.replace('edit/', ''));
            }).fail(function(response){
            var data = $.parseJSON(response.responseText);
            $('.alert', form).remove();
            for (i = 0; i < data.failed_inputs.length; i++) {
                $('[name="' + data.failed_inputs[i][0] + '"]', form).focus().parent().append('<div class="alert alert-danger" role="alert">' + data.failed_inputs[i][1] + '</div>');
            }
            actionButton.button('reset');
        });
        return false;
    });

    // handles the creation/addition of a new course in the 'courses' view
    $(document).on('submit', '.modal-add-course form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var data = $.parseJSON(response);
            var newRow = $('#course-0').clone(true).attr('id', 'course-' + data.course.id).attr('data-action', data.course.url).hide();
            $('.course-none-message', newRow).remove();
            $('.course-id', newRow).html('<div>' + data.course.id + '</div>');
            $('.course-name', newRow).html('<a href="' + data.course.assignments_url + '" title="' + data.course.title + '">' + data.course.title + '</a>');
            $('.course-assignments-url', newRow).attr('href', data.course.assignments_url);
            $('.course-students-url', newRow).attr('href', data.course.students_url);
            $('.course-list').append(newRow);
            newRow.slideToggle(300);
            actionButton.button('reset');
            form.closest('.modal').modal('hide');
        }).fail(function(response){
            var data = $.parseJSON(response.responseText);
            $('.alert', form).remove();
            for (i = 0; i < data.failed_inputs.length; i++) {
                $('[name="' + data.failed_inputs[i][0] + '"]', form).focus().after('<div class="alert alert-danger" role="alert">' + data.failed_inputs[i][1] + '</div>').show();
            }
            actionButton.button('reset');
        });
        return false;
    });

    // handles the approval/disapproval of students in the 'students' view
    $(document).on('submit', '.approve-student-form, .unapprove-student-form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var targetRow = form.closest('.student');
            if (targetRow.hasClass('student-approved')) {
                targetRow.removeClass('student-approved').addClass('student-unapproved list-group-item-warning');
            } else {
                targetRow.removeClass('student-unapproved list-group-item-warning').addClass('student-approved');
            }
            actionButton.button('reset');
        });
        return false;
    });

    // handles the removal of courses from the 'courses' view
    $(document).on('submit', '.modal-remove-course form', function(){
        var form = $(this);
        var formData = form.serializeArray();
        var actionButton = $('button[type="submit"][data-clicked="true"]', form);
        formData.push({ name: actionButton.attr('name'), value: actionButton.val() });
        actionButton.button('loading');
        var response = $.post(form.attr('action'), formData).done(function(response){
            var target = $('input[name="course_id"]', form).val();
            $('#course-' + target).slideToggle(300, function(){
                $(this).remove();
            });
            actionButton.button('reset');
            form.closest('.modal').modal('hide');
        });
        return false;
    });

    // handles identifying which button submitted the form
    $(document).on('click', 'form button[type="submit"]', function(){
        var form = $(this).closest('form');
        $('button[type="submit"]', form).removeAttr('data-clicked');
        $(this).attr('data-clicked', 'true');
    });

    // handles the highlighting of the target field in modals on 'courses' view
    $(document).on('shown.bs.modal', '.modal-add-course', function(){
        $('input[name="course_title"]', this).focus();
        $('input[name="course_id"]', this).focus();
    });

    // handles the filling out of course removal confirmation input fields
    $(document).on('show.bs.modal', '.modal-remove-course', function(e){
        var target = $(e.relatedTarget);
        var targetRow = target.closest('.course');
        var courseName = $('.course-name', targetRow);
        var courseID = $('.course-id div', targetRow);
        $('.course-title', this).text($.trim(courseName.text()));
        $('input[name="course_id"]', this).val(courseID.text());
        $('form', this).attr('action', targetRow.attr('data-action'));
    });

    // handles clearing the fields in modals on successful course addition
    $(document).on('hidden.bs.modal', '.modal-add-course', function(){
        $('.alert', this).remove();
        $('input[name="course_title"]', this).val('');
        $('input[name="course_id"]', this).val('');
    });

});
