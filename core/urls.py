from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
import core.views as views
from . import paper_forwarding
# import core.oldviews as oldviews
    
urlpatterns = [
    

    path("assessment/<int:pk>/", views.assessment_detail, name="assessment_detail"),
    
    #dedicated paper forwarding Logic
    path("assessment/<int:pk>/to-assessor/", paper_forwarding.send_to_assessor, name="send_to_assessor"),
    path("assessment/<int:pk>/to-moderator/", paper_forwarding.send_to_moderator, name="send_to_moderator"),
    path("assessment/<int:pk>/to-qcto/", paper_forwarding.send_to_qcto, name="send_to_qcto"),
    path("assessment/<int:pk>/to-etqa/", paper_forwarding.send_to_etqa, name="send_to_etqa"),
    path("assessment/<int:pk>/approve/", paper_forwarding.approve_etqa, name="approve_etqa"),
    # Admin URLs
    path('administrator/', views.admin_dashboard, name='admin_dashboard'),
    path('administrator/user-management/', views.user_management, name='user_management'),
    path('administrator/qualifications/', views.qualification_management_view, name='manage_qualifications'),
    path('administrator/assessment-centres/', views.assessment_centres_view, name='assessment_centres'),
    path('administrator/review-saved/', views.review_saved_selector, name='review_saved_selector'),
    path('administrator/review-saved/<int:paper_pk>/', views.load_saved_paper_view, name='load_saved_paper'),

    # Question Bank URLs
    path('databank/', views.databank_view, name='databank'),
    path('add-question/', views.add_question, name='add_question'),
    path('add-case-study/', views.add_case_study, name='add_case_study'),
    
    # User Management URLs
    path('update-user-role/<int:user_id>/', views.update_user_role, name='update_user_role'),
    path('update-user-qualification/<int:user_id>/', views.update_user_qualification, name='update_user_qualification'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),

    # Assessment Centre URLs
    path('edit-centre/<int:centre_id>/', views.edit_assessment_centre, name='edit_assessment_centre'),
    path('delete-centre/<int:centre_id>/', views.delete_assessment_centre, name='delete_assessment_centre'),

    # Assessor URLs
    path('assessor/', views.assessor_dashboard, name='assessor_dashboard'),
    path('assessor/upload/', views.upload_assessment, name='upload_assessment'),
    path('assessor/reports/', views.assessor_reports, name='assessor_reports'),
    path('assessor/archive/', views.assessment_archive, name='assessment_archive'),
    path('assessor/view/<str:eisa_id>/', views.view_assessment, name='view_assessment'),

    # Moderator URLs
    path('moderator/', views.moderator_developer_dashboard, name='moderator_developer'),
    path('moderate/<int:paper_id>/', views.moderate_assessment, name='moderate_assessment'),
    path('add-feedback/<str:eisa_id>/', views.add_feedback, name='add_feedback'),

    # ETQA URLs
    path('etqa/', views.etqa_dashboard, name='etqa_dashboard'),

    # QCTO URLs
    path('qcto/', views.qcto_dashboard, name='qcto_dashboard'),
    path('qcto/moderate/<str:eisa_id>/', views.qcto_moderate_assessment, name='qcto_moderate_assessment'),
    path('qcto/reports/', views.qcto_reports, name='qcto_reports'),
    path('qcto/compliance/', views.qcto_compliance, name='qcto_compliance'),
    path('qcto/review/', views.qcto_assessment_review, name='qcto_assessment_review'),
    path('qcto/archive/', views.qcto_archive, name='qcto_archive'),
    path('qcto/view/<str:eisa_id>/', views.qcto_view_assessment, name='qcto_view_assessment'),

    # Authentication URLs
    path('', views.custom_login, name='custom_login'),
    path('logout/', views.custom_logout, name='logout'),  # Change name from 'custom_login' to 'logout'
    path('register/', views.register, name='register'),
    path('default/', views.default_page, name='default'),

    # Student URLs
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/approved-assessments/', views.approved_assessments_for_learners, name='approved_assessments_for_learners'),
    path('student/assessments/<int:assessment_id>/write/', views.write_exam, name='write_exam'),
    path('student/assessments/<int:assessment_id>/submit/', views.submit_exam, name='submit_exam'),
    
    #Demo Student URLS to be robusted later
    path('student/papers/', views.papers_demo, name='papers_demo'),
    path('student/papers/<int:paper_id>/write/', views.write_paper_simple, name='write_paper_simple'),
    path('student/papers/<int:paper_id>/submit/', views.submit_paper_simple, name='submit_paper_simple'),

    # Tracking URLs
    path('track/', views.assessment_progress_tracker, name='assessment_progress_tracker'),

    # Randomize Paper Structure URL
    path('randomize/paper/<int:paper_pk>/', 
         views.randomize_paper_structure_view, 
         name='randomize_paper_structure'),

    # Save Blocks URL
  # urls.py
path('save-blocks/<int:paper_id>/', views.save_blocks_view, name='save_blocks')

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)