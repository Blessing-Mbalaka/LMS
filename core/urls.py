from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from core.views import (
    generate_tool_page,
    generate_tool, save_extracted_questions, beta_paper_tables_view,
    assessor_dashboard,
    view_assessment,
    upload_assessment,
    assessment_archive,
    assessor_reports,
    submit_generated_paper,
    add_question, auto_classify_blocks,
    add_case_study,
    add_feedback,
    moderator_developer_dashboard,
    moderate_assessment, paper_as_is_view,
    checklist_stats,
    toggle_checklist_item, qcto_dashboard, qcto_moderate_assessment, qcto_compliance,qcto_assessment_review,
    qcto_archive,
    qcto_reports,
    qcto_view_assessment,
    qcto_latest_assessment_detail,
    databank_view, clean_questions,
    admin_dashboard,
    assessment_centres_view,
    user_management,
    toggle_user_status,
    update_user_qualification,
    update_user_role,
    custom_login, custom_logout,
edit_assessment_centre,
delete_assessment_centre, auto_fix_blocks,
qualification_management_view, register,
default_page, student_results, beta_paper_extractor, #Beta_paper extractor might delete if it does not work...
assessment_progress_tracker,
etqa_dashboard, assessment_center_view, submit_to_center,
approve_by_etqa, reject_by_etqa, student_assessment, student_dashboard, submit_exam, student_results



)

urlpatterns = [
    path('administrator/dashboard/', admin_dashboard, name='admin_dashboard'),

    #paper extraction views still in development
    path('administrator/auto-fix-blocks/', auto_fix_blocks, name='auto_fix_blocks'),
    path('administrator/auto-classify-blocks/', auto_classify_blocks, name='auto_classify_blocks'),
    #path('administrator/auto-classify/', auto_classify_blocks, name='auto_classify_blocks'),
    path("administrator/review-paper/", paper_as_is_view, name="review_paper"),

    path("administrator/beta-paper-tables/", beta_paper_tables_view, name="beta_paper_tables"),
    path('administrator/beta-paper/', beta_paper_extractor, name='beta_paper'),
     path("api/clean-questions/", clean_questions, name="clean_questions"),
    path('administrator/save-extracted/', save_extracted_questions, name='save_extracted_questions'),
#___________________________________________________________________________________________________________
    path('awaiting-activation/', default_page, name='default'),
    path('assessor/dashboard/', assessor_dashboard, name='assessor_dashboard'),
    path('assessor/assessment/<str:eisa_id>/', view_assessment, name='view_assessment'),
    path('upload_assessment/', upload_assessment, name='upload_assessment'),
    path('assessor-developer/assessment_archive/', assessment_archive, name='assessment_archive'),
    path('reports/', assessor_reports, name='assessor_reports'),
    path('generate-paper/', generate_tool_page, name='generate_tool_page'),
    path('api/generate-paper/', generate_tool, name='generate_tool'),
    path("submit-generated-paper/", submit_generated_paper, name="submit_generated_paper"),
    path('add-question/', add_question, name='add_question'), 
    path('add-case-study/', add_case_study, name='add_case_study'),
    path("moderator/", moderator_developer_dashboard, name="moderator_developer"),
    path("moderator/<str:eisa_id>/moderate/", moderate_assessment, name="moderate_assessment"),
    path("moderator/<str:eisa_id>/feedback/add/", add_feedback, name="add_feedback"),
    path( "moderator/checklist/<int:item_id>/toggle/", toggle_checklist_item,name="toggle_checklist_item"),
    path( "moderator/checklist/stats/", checklist_stats,name="checklist_stats"),
    path('qcto/dashboard/', qcto_dashboard, name='qcto_dashboard'),
    #_____________________________________________________________
    path('etqa/dashboard/', etqa_dashboard, name='etqa_dashboard'),
    #______________________________________________________________
    path('qcto/<str:eisa_id>/moderate/', qcto_moderate_assessment, name='qcto_moderate_assessment'),
    path('qcto/compliance/', qcto_compliance, name='qcto_compliance'),
    path('qcto/review/', qcto_assessment_review, name='qcto_assessment_review'),
    path('qcto/archive/', qcto_archive, name='qcto_archive'),
    path('qcto/reports/', qcto_reports, name='qcto_reports'),
    path('qcto/<str:eisa_id>/view/', qcto_view_assessment, name='qcto_view_assessment'),
    path("qcto/view-latest/", qcto_latest_assessment_detail, name="qcto_latest_assessment_detail"),
    path("administrator/databank/", databank_view, name='databank'),
    path("administrator/dashboard/", admin_dashboard, name='admin_dashboard'),
    path("administrator/assessment-centres/", assessment_centres_view, name='assessment_centres'),
    path('administrator/assessment-centres/edit/<int:centre_id>/', edit_assessment_centre, name='edit_assessment_centre'),
    path('administrator/assessment-centres/delete/<int:centre_id>/', delete_assessment_centre, name='delete_assessment_centre'),
    path("administrator/user-management/", user_management, name='user_management'),
    path('update-user-role/<int:user_id>/', update_user_role, name='update_user_role'),
    path('update-user-qualification/<int:user_id>/',update_user_qualification, name='update_user_qualification'),
    path('toggle-user-status/<int:user_id>/', toggle_user_status, name='toggle_user_status'),
    path('administrator/qualifications/', qualification_management_view, name='manage_qualifications'),

#Login and logout path**********************************************************
     path('logout/', custom_logout, name='logout'),
    path('', custom_login, name='custom_login'),
     path("register/", register, name="register"),
#********************************************************************
#Assessment progress Tracker this is for tracking who has the paper...
    path('assessment-tracker/', assessment_progress_tracker, name='assessment_progress_tracker'),

# paths to create batch and view all the approved assessments______________________________________________

    # path('create-batch/', create_batch, name='create_batch'),
 path('assessment-center/', assessment_center_view, name='assessment_center'),   

# paths to submit batch to assessment html page_______________________________________________________
    path('submit-to-center/<int:batch_id>/', submit_to_center, name='submit_to_center'),


     path('etqa/approve/<int:assessment_id>/', approve_by_etqa, name='approve_by_etqa'),
    path('etqa/reject/<int:assessment_id>/', reject_by_etqa, name='reject_by_etqa'),



     # Student-facing URLs
     # 1) Dashboard: list “ready” assessments for this user
    path(
        'student/',
        student_dashboard,
        name='student_dashboard'
    ),

    # 2) Writing an assessment
    path(
        'student/assessment/<int:assessment_id>/',
        student_assessment,
        name='student_assessment'
    ),

    # 3) Submitting answers
    path(
        'student/submit-exam/<int:assessment_id>/',
        submit_exam,
        name='submit_exam'
    ),

    # 4) Viewing past results
    path('student/results/', student_results, name='student_results'),


    
]

    
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




   
  