jQuery(document).ready(function($){

    $('#createNewCourseModal').on('shown.bs.modal', function(){
        $('input[name="course_title"]', this).focus();
    });

    $('#deleteCourseModal').on('shown.bs.modal', function(e){
        var target = $(e.relatedTarget);
        this.caller = target.closest('.course');
        var courseID = target.data('course-id');
        $('input[name="course_id"]', this).val(courseID);
    });

    $('#createNewCourseForm').submit(function(){
        var form = $(this);
        $('input[name="ajax"]', form).val(true);
        var formData = form.serialize();
        var courseNone = $('.course-none');
        var modal = form.closest('.modal');
        var actionButton = form.find('input[type="submit"]');
        var courseList = $('.course-list');
        actionButton.button('loading');
        var response = $.post('/courses', formData).success(function(response){
            var data = $.parseJSON(response);
            var newRow = $('.course-list .course:first-of-type').clone(true);
            $('.attr-course-id', newRow).html('<div>' + data.course_id + '</div>');
            $('.attr-course-name', newRow).html('<a href="' + data.course_url + '" title="' + data.course_title + '">' + data.course_title + '</a>');
            $('.attr-course-enrolled, .attr-course-pending', newRow).text('0');
            $('.attr-course-remove', newRow).removeClass('hidden');
            newRow.removeClass('course-none hidden');
            newRow.attr('id', 'course-' + data.course_id);
            courseNone.addClass('hidden');
            courseNone.before(newRow);
            actionButton.button('reset');
            modal.modal('hide');
        });
        return false;
    });

    $('#deleteCourseForm').submit(function(){
        var form = $(this);
        $('input[name="ajax"]', form).val(true);
        var formData = form.serialize();
        var modal = form.closest('.modal');
        var actionButton = form.find('input[type="submit"]');
        actionButton.button('loading');
        var response = $.post('/courses', formData).success(function(response){
            var target = $('input[name="course_id"]').val();
            $('#course-' + target).remove();
            if ( $('.course-list .course').length < 2 ) {
                $('.course-none').removeClass('hidden');
            }
            actionButton.button('reset');
            modal.modal('hide');
        });
        return false;
    });

});