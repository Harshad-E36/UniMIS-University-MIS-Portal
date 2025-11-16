from django.shortcuts import render, redirect
from .models import College, CollegeProgram, Taluka, District, Discipline, Programs, CollegeType, BelongsTo, academic_year, student_aggregate_master
from django.db.models import Prefetch
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from functools import wraps
from django.db import transaction
import json
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


# Create your views here.

def ajax_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Session expired. Please log in again.', 'status': 302})
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def get_client_ip(request):
    """Get the real client IP address from request headers"""
    x_forwarded_for = request.META.get(('HTTP_X_FORWARDED_FOR'))
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip


# Helper function to safely convert values to int
def _to_int(value, default=0):
    """Convert value to int safely, treating None/'' as default."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')

    print(Discipline.objects.all())
    return render(request, 'index.html', {
        "Colleges": College.objects.filter(is_deleted=False),
        "disciplines": Discipline.objects.all(),
        "Collegetype": CollegeType.objects.all(),
        "BelongsTo": BelongsTo.objects.all(),
        "programs": Programs.objects.all()
    })
   

def college_master(request):
    return render(request, 'college_master.html', {"disciplines" : Discipline.objects.all(), "Collegetype" : CollegeType.objects.all(), "BelongsTo": BelongsTo.objects.all()}) 


def student_master(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'student_master.html', {"academic_year": academic_year.objects.all()})



@ajax_login_required
def add_edit_record(request):
    if request.method != "POST":
        return JsonResponse({"status": 400, "message": "Invalid method"}, status=400)

    # Safe ID parsing
    raw_id = request.POST.get('id', '').strip()
    try:
        record_id = int(raw_id) if raw_id else 0
    except ValueError:
        return JsonResponse({"status": 400, "message": "Invalid ID"}, status=400)

    college_code = request.POST.get('college_code')
    college_name = request.POST.get('college_name')
    address = request.POST.get('address')
    country = request.POST.get('country')
    state = request.POST.get('state')
    district = request.POST.get('district')
    taluka = request.POST.get('taluka')
    city = request.POST.get('city')
    pincode = request.POST.get('pincode')
    college_type = request.POST.get('college_type')
    belongs_to = request.POST.get('belongs_to')
    affiliated = request.POST.get('affiliated_to')

    # Parse JSON safely
    programs_json = request.POST.get('disciplines_programs', '[]')
    try:
        programs = json.loads(programs_json)
    except Exception:
        return JsonResponse({"status": 400, "message": "Invalid programs JSON"}, status=400)

    # =============== EDIT MODE =============== 
    if record_id > 0:
        try:
            # change: make sure we don't edit a soft-deleted college
            college = College.objects.get(id=record_id, is_deleted=False)
        except College.DoesNotExist:
            return JsonResponse({"status": 404, "message": "Record not found"}, status=404)

        with transaction.atomic():
            # ---- Update college basic data ----
            college.College_Code = college_code
            college.College_Name = college_name
            college.address = address
            college.country = country
            college.state = state
            college.District = district
            college.taluka = taluka
            college.city = city
            college.pincode = pincode
            college.college_type = college_type
            college.belongs_to = belongs_to
            college.affiliated = affiliated
            college.updated_by = get_client_ip(request)
            college.save()

            # ---- Soft-delete all programs for this college first ----
            CollegeProgram.objects.filter(College=college).update(is_deleted=True)

            # Track active programs after this update
            active_program_ids = []

            # ---- Recreate / reactivate programs from request ----
            for item in programs:
                discipline = item.get('Discipline')
                program_name = item.get('ProgramName')

                if not discipline or not program_name:
                    # Skip invalid items
                    continue

                cp, created = CollegeProgram.objects.get_or_create(
                    College=college,
                    Discipline=discipline,
                    ProgramName=program_name,
                    defaults={'is_deleted': False}
                )

                # If it already exists but was soft-deleted, reactivate it
                if not created and cp.is_deleted:
                    cp.is_deleted = False
                    cp.save(update_fields=['is_deleted'])

                active_program_ids.append(cp.id)

            # ---- Sync student_aggregate_master with active programs ----
            if active_program_ids:
                # We only want to affect aggregates for removed programs,
                # and we must avoid unique constraint conflicts:
                # (College, Program, Academic_Year, is_deleted)
                to_soft_delete = student_aggregate_master.objects.filter(
                    College=college,
                    is_deleted=False
                ).exclude(
                    Program_id__in=active_program_ids
                )

                # Soft-delete one by one safely
                for agg in to_soft_delete.select_for_update():
                    conflict_qs = student_aggregate_master.objects.filter(
                        College=agg.College,
                        Program=agg.Program,
                        Academic_Year=agg.Academic_Year,
                        is_deleted=True
                    ).exclude(pk=agg.pk)

                    if conflict_qs.exists():
                        # There is an OLDER soft-deleted row.
                        old_soft_deleted = conflict_qs.first()

                        # HARD delete the old stale row (cleanup)
                        old_soft_deleted.delete()

                        # NOW safely soft-delete the active row
                        agg.is_deleted = True
                        agg.save(update_fields=['is_deleted'])
                    else:
                        # No duplicates → normal soft delete
                        agg.is_deleted = True
                        agg.save(update_fields=['is_deleted'])

            else:
                # No active programs left: soft-delete all aggregates for this college
                to_soft_delete = student_aggregate_master.objects.filter(
                    College=college,
                    is_deleted=False
                )

                for agg in to_soft_delete.select_for_update():
                    conflict_qs = student_aggregate_master.objects.filter(
                        College=agg.College,
                        Program=agg.Program,
                        Academic_Year=agg.Academic_Year,
                        is_deleted=True
                    ).exclude(pk=agg.pk)

                    if conflict_qs.exists():
                        agg.delete()
                    else:
                        agg.is_deleted = True
                        agg.save(update_fields=['is_deleted'])

        return JsonResponse({"status": 200, "message": "Record updated successfully"})

    # =============== ADD MODE =============== 
    with transaction.atomic():
        college = College.objects.create(
            College_Code=college_code,
            College_Name=college_name,
            address=address,
            country=country,
            state=state,
            District=district,
            taluka=taluka,
            city=city,
            pincode=pincode,
            college_type=college_type,
            belongs_to=belongs_to,
            affiliated=affiliated,
            created_by=get_client_ip(request)
        )

        for item in programs:
            discipline = item.get('Discipline')
            program_name = item.get('ProgramName')

            if not discipline or not program_name:
                continue

            CollegeProgram.objects.create(
                College=college,
                Discipline=discipline,
                ProgramName=program_name
            )
        # (Usually no student_aggregate_master rows yet in ADD mode)

    return JsonResponse({"status": 201, "message": "Record added successfully"})




@ajax_login_required
def delete_record(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        record = College.objects.get(id = id)
        record.is_deleted = True
        record.save()

        response_data = {
            'message' : 'record deleted successfully',
            'status' : 204
        }
        return JsonResponse(response_data)
    

def user_status(request):
    if request.user.is_authenticated:
        response_data = {
            'is_authenticated' : True,
            'username' : request.user.username,
            'status' : 200,
            'total_colleges_count' : College.objects.filter(is_deleted = False).count(),
            # aggreagate function also returns dictionary if no records found so we have to handle that case by using 'or 0' at the end
            'total_students_count' : student_aggregate_master.objects.filter(is_deleted = False).aggregate(total=Sum('total_students'))['total'] or 0
        }
        print(response_data)
    else:
        response_data = {
            'is_authenticated' : False,
            'status' : 401
        }
    return JsonResponse(response_data)  


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username = username).exists():
            response_data = {
                'message' : 'Username already exists',
                'status' : 400
            }
            return JsonResponse(response_data)
        
        if User.objects.filter(email = email).exists():
            print("inside")
            response_data = {
                'message' : 'Email already exists',
                'status' : 400
            }
            return JsonResponse(response_data)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        response_data = {
            'message' : 'User created successfully',
            'status' : 201
        }
        return JsonResponse(response_data)
    

def user_login(request):
    # If already logged in → go home
    if request.user.is_authenticated:
        return redirect('home')

    # If form is POST (login attempt)
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me',0)  # '1' if checked, 0 if not
        print(remember_me)

        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            return JsonResponse({'status': 401, 'message': 'Invalid email or password'})

        user = authenticate(request, username=username, password=password)


        if user:
            login(request, user)
            # Set session expiry based on "Remember Me"
            if remember_me == '1':
                request.session.set_expiry(21600)  # 2 weeks
            return JsonResponse({'status': 200, 'message': 'Login successful'})

        return JsonResponse({'status': 401, 'message': 'Invalid email or password'})

    # Show login page
    return render(request, 'login_page.html')
        
        
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        response_data = {
            'message' : 'logout successful',
            'status' : 200
        }
        return JsonResponse(response_data)
    

def apply_filters(request):
    if request.method == "POST":
        college_codes = request.POST.getlist('ColegeCode[]')
        college_names = request.POST.getlist('CollegeName[]')
        districts = request.POST.getlist('District[]')
        talukas = request.POST.getlist('Taluka[]')
        college_types = request.POST.getlist('CollegeType[]')
        belongs_tos = request.POST.getlist('BelongsTo[]')
        disciplines = request.POST.getlist('Discipline[]')
        programs = request.POST.getlist('Programs[]')

        print(college_codes, college_names, districts, talukas, college_types, belongs_tos, disciplines, programs)

        filter_criteria = Q(is_deleted = False)

        if college_codes:
            filter_criteria &= Q(College_Code__in = college_codes)
        
        if college_names:
            filter_criteria &= Q(College_Name__in = college_names)
        
        if districts:
            filter_criteria &= Q(District__in = districts)
        
        if talukas:
            filter_criteria &= Q(taluka__in = talukas)
        
        if college_types:
            filter_criteria &= Q(college_type__in = college_types)
        
        if belongs_tos:
            filter_criteria &= Q(belongs_to__in = belongs_tos)
        
         # ============ APPLY PROGRAM/DISCIPLINE FILTERS ============
        if disciplines:
            filter_criteria &= Q(college_programs__Discipline__in=disciplines)

        if programs:
            filter_criteria &= Q(college_programs__ProgramName__in=programs)
        


         # ==== GET FILTERED COLLEGE IDs ====
        filtered_colleges = College.objects.filter(filter_criteria).distinct()
        print(filtered_colleges.count())
        filtered_college_ids = list(filtered_colleges.values_list("id", flat=True))

        # ==== AGGREGATE ONLY total_students ====
        agg_qs = student_aggregate_master.objects.filter(
            College_id__in=filtered_college_ids,
            is_deleted=False
        )

        total_students_sum = agg_qs.aggregate(total=Sum("total_students"))["total"] or 0
        print(total_students_sum)

        return JsonResponse({
            "status": 200,
            "message": "Filters applied successfully",
            "filtered_colleges_count": filtered_colleges.count(),
            "total_students": total_students_sum
        })

    

def clear_filters(request):
    if request.method == "GET":
        response_data = {
            'status' : 200,
            'total_colleges_count' : College.objects.filter(is_deleted = False).count(),
            'total_students_count' : student_aggregate_master.objects.filter(is_deleted = False).aggregate(total=Sum('total_students'))['total'] or 0
        }
        return JsonResponse(response_data)

    return JsonResponse({"status": "error"}, status=400)


def get_talukas(request):
    if request.method == "GET":
        district_name = request.GET.get('district')
        if not district_name:
            return JsonResponse({'talukas': []})
        
        talukas = Taluka.objects.filter(District__DistrictName=district_name).values_list('TalukaName', flat=True)
        print(talukas)
        return JsonResponse({'talukas': list(talukas)})
    return JsonResponse({'talukas': []})


def get_programs_for_discipline(request):
    disciplines = request.GET.getlist('discipline')
    print(disciplines)  # Get from AJAX call
    response_data = {}

    for discipline_name in disciplines:
        # Fetch all programs related to this discipline from DB
        programs = Programs.objects.filter(
            Discipline__DisciplineName=discipline_name
        ).values_list('ProgramName', flat=True)

        # If no programs found, use default placeholder
        if programs:
            response_data[discipline_name] = list(programs)
        else:
            response_data[discipline_name] = ["No programs available"]

    return JsonResponse(response_data)

@ajax_login_required
def get_college_data(request):
    if request.method != "GET":
        return JsonResponse({'status': 400, 'message': 'Invalid request'})

    college_code = request.GET.get('college_code')
    academic_year = request.GET.get('academic_year')
    mode = request.GET.get('mode', 'add')

    if not college_code:
        return JsonResponse({'status': 400, 'message': 'Missing college_code'})

    try:
        college = College.objects.get(College_Code=college_code, is_deleted=False)
    except College.DoesNotExist:
        return JsonResponse({'status': 404, 'message': 'College not found'})

    # ---------- Build discipline -> sorted(programs) map ----------
    all_programs = (
        CollegeProgram.objects
        .filter(College=college, is_deleted=False)
        .values("Discipline", "ProgramName")
        .order_by("Discipline", "ProgramName")             # <-- alphabetical sorting HERE
    )

    discipline_map = {}
    for item in all_programs:
        disc = item.get("Discipline") or "Unspecified"
        prog = item.get("ProgramName") or "Unnamed Program"
        discipline_map.setdefault(disc, []).append(prog)

    # Ensure alphabetical discipline ordering
    discipline_map = {
        disc: sorted(progs, key=lambda x: x.lower())
        for disc, progs in sorted(discipline_map.items(), key=lambda x: x[0].lower())
    }

    full_address = f"{college.address}, {college.taluka}, {college.District} - {college.pincode}"

    base_college_data = {
        "College_Code": college.College_Code,
        "College_Name": college.College_Name,
        "address": full_address,
        "District": college.District,
        "Taluka": college.taluka,
        "pincode": college.pincode,
        "country": getattr(college, "country", ""),
        "state": getattr(college, "state", ""),
        "affiliated": getattr(college, "affiliated", ""),
        "programs": discipline_map
    }

    # ADD MODE
    if mode == "add":
        return JsonResponse({
            "status": 200,
            "mode": "add",
            "academic_year": academic_year,
            "college_data": base_college_data,
            "records": {}
        })

    # EDIT MODE
    if mode == "edit":
        if not academic_year:
            return JsonResponse({'status': 400, 'message': 'Missing academic_year'})

        aggregates = student_aggregate_master.objects.filter(
            College=college,
            Academic_Year=academic_year,
            is_deleted=False
        ).select_related("Program")

        if not aggregates.exists():
            return JsonResponse({
                "status": 404,
                "message": "No records found for this year"
            })

        filled_records = {}

        for agg in aggregates:
            prog_name = agg.Program.ProgramName if agg.Program else f"program_{agg.pk}"

            filled_records[prog_name] = {
                "total_students": agg.total_students,
                "gender": {
                    "male": agg.total_male,
                    "female": agg.total_female,
                    "others": agg.total_others,
                },
                "category": {
                    "open": agg.total_open,
                    "obc": agg.total_obc,
                    "sc": agg.total_sc,
                    "st": agg.total_st,
                    "nt": agg.total_nt,
                    "vjnt": agg.total_vjnt,
                    "ews": agg.total_ews,
                },
                "religion": {
                    "hindu": agg.total_hindu,
                    "muslim": agg.total_muslim,
                    "sikh": agg.total_sikh,
                    "christian": agg.total_christian,
                    "jain": agg.total_jain,
                    "buddhist": agg.total_buddhist,
                    "other": agg.total_other_religion,
                },
                "disability": {
                    "none": agg.total_no_disability,
                    "lowvision": agg.total_low_vision,
                    "blindness": agg.total_blindness,
                    "hearing": agg.total_hearing,
                    "locomotor": agg.total_locomotor,
                    "autism": agg.total_autism,
                    "other": agg.total_other_disability,
                }
            }

        return JsonResponse({
            "status": 200,
            "mode": "edit",
            "academic_year": academic_year,
            "college_data": base_college_data,
            "records": filled_records
        })

    return JsonResponse({"status": 400, "message": "Invalid mode"})




@ajax_login_required
def add_student_aggregate(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")
        
        college_code = payload.get('college_code')
        academic_year = payload.get('academic_year')
        records = payload.get('records', [])

        if not college_code or not academic_year:
            return JsonResponse({'status': 400, 'message': 'Missing required fields'})

        try:
            college = College.objects.get(College_Code=college_code, is_deleted=False)      
        except College.DoesNotExist:
            return JsonResponse({'status': 404, 'message': 'College not found'})
        
        if not isinstance(records, dict) or len(records) == 0:
            return JsonResponse({"status": 400, "message": "No records provided"}, status=400)
        
        saved = []
        errors = []

        with transaction.atomic():
            for program_name, data in records.items():
                program_obj = CollegeProgram.objects.filter(
                    College=college,
                    ProgramName=program_name,
                    is_deleted=False
                ).first()
                
                if not program_obj:
                    errors.append({
                        "program": program_name,
                        "error": f"Program '{program_name}' not found for college '{college_code}'"
                    })
                    continue
                
                # ---- parse numeric fields safely ----
                total_students = _to_int(data.get("total_students"), 0)

                gender = data.get("gender", {}) or {}
                male = _to_int(gender.get("male"), 0)
                female = _to_int(gender.get("female"), 0)
                others = _to_int(gender.get("others") or gender.get("other"), 0)

                category = data.get("category", {}) or {}
                total_open = _to_int(category.get("open") or category.get("general"), 0)
                total_obc = _to_int(category.get("obc"), 0)
                total_sc = _to_int(category.get("sc"), 0)
                total_st = _to_int(category.get("st"), 0)
                total_nt = _to_int(category.get("nt"), 0)
                total_vjnt = _to_int(category.get("vjnt"), 0)
                total_ews = _to_int(category.get("ews"), 0)

                religion = data.get("religion", {}) or {}
                total_hindu = _to_int(religion.get("hindu"), 0)
                total_muslim = _to_int(religion.get("muslim"), 0)
                total_sikh = _to_int(religion.get("sikh"), 0)
                total_christian = _to_int(religion.get("christian"), 0)
                total_jain = _to_int(religion.get("jain"), 0)
                total_buddhist = _to_int(religion.get("buddhist"), 0)
                total_other_religion = _to_int(religion.get("other"), 0)

                dis = data.get("disability", {}) or {}
                total_no_disability = _to_int(dis.get("none") or dis.get("no_disability"), 0)
                total_low_vision = _to_int(dis.get("lowvision"), 0)
                total_blindness = _to_int(dis.get("blindness"), 0)
                total_hearing = _to_int(dis.get("hearing"), 0)
                total_locomotor = _to_int(dis.get("locomotor"), 0)
                total_autism = _to_int(dis.get("autism"), 0)
                total_other_disability = _to_int(dis.get("other"), 0)

                defaults = {
                    "total_students": total_students,
                    "total_male": male,
                    "total_female": female,
                    "total_others": others,

                    "total_open": total_open,
                    "total_obc": total_obc,
                    "total_sc": total_sc,
                    "total_st": total_st,
                    "total_nt": total_nt,
                    "total_vjnt": total_vjnt,
                    "total_ews": total_ews,

                    "total_hindu": total_hindu,
                    "total_muslim": total_muslim,
                    "total_sikh": total_sikh,
                    "total_christian": total_christian,
                    "total_jain": total_jain,
                    "total_buddhist": total_buddhist,
                    "total_other_religion": total_other_religion,

                    "total_no_disability": total_no_disability,
                    "total_low_vision": total_low_vision,
                    "total_blindness": total_blindness,
                    "total_hearing": total_hearing,
                    "total_locomotor": total_locomotor,
                    "total_autism": total_autism,
                    "total_other_disability": total_other_disability,
                }

                try:
                    client_ip = get_client_ip(request)

                    # ✅ Check only ACTIVE record (is_deleted = False)
                    existing = student_aggregate_master.objects.filter(
                        College=college,
                        Program=program_obj,
                        Academic_Year=academic_year,
                        is_deleted=False,
                    ).first()

                    if existing:
                        errors.append({
                            "program": program_name,
                            "error": "Record already exists for this college, program and academic year"
                        })
                        continue

                    # 🆕 No active record → create a completely NEW one
                    obj = student_aggregate_master.objects.create(
                        College=college,
                        Program=program_obj,
                        Academic_Year=academic_year,
                        is_deleted=False,
                        created_by=client_ip,
                        **defaults,
                    )

                    saved.append({"program": program_name, "id": obj.pk, "created": True})

                except Exception as e:
                    errors.append({"program": program_name, "error": f"DB error: {str(e)}"})
                    continue

        response_status = 200 if not errors else 207
        resp = {
            "status": response_status,
            "saved": saved,
            "errors": errors,
            "summary": {
                "created": sum(1 for s in saved if s.get("created")),
                "updated": 0,   # no updates here
                "failed": len(errors)
            }
        }
        return JsonResponse(resp)
    


@ajax_login_required
def update_student_aggregate(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON")

        college_code = payload.get('college_code')
        academic_year = payload.get('academic_year')
        records = payload.get('records', [])

        if not college_code or not academic_year:
            return JsonResponse({'status': 400, 'message': 'Missing required fields'})

        try:
            college = College.objects.get(College_Code=college_code, is_deleted=False)
        except College.DoesNotExist:
            return JsonResponse({'status': 404, 'message': 'College not found'})

        if not isinstance(records, dict) or len(records) == 0:
            return JsonResponse({"status": 400, "message": "No records provided"}, status=400)

        updated = []
        created = []
        errors = []

        with transaction.atomic():
            for program_name, data in records.items():
                program_obj = CollegeProgram.objects.filter(
                    College=college,
                    ProgramName=program_name,
                    is_deleted=False
                ).first()

                if not program_obj:
                    errors.append({
                        "program": program_name,
                        "error": f"Program '{program_name}' not found for college '{college_code}'"
                    })
                    continue

                # ---- parse numeric fields safely (same as add) ----
                total_students = _to_int(data.get("total_students"), 0)

                gender = data.get("gender", {}) or {}
                male = _to_int(gender.get("male"), 0)
                female = _to_int(gender.get("female"), 0)
                others = _to_int(gender.get("others") or gender.get("other"), 0)

                category = data.get("category", {}) or {}
                total_open = _to_int(category.get("open") or category.get("general"), 0)
                total_obc = _to_int(category.get("obc"), 0)
                total_sc = _to_int(category.get("sc"), 0)
                total_st = _to_int(category.get("st"), 0)
                total_nt = _to_int(category.get("nt"), 0)
                total_vjnt = _to_int(category.get("vjnt"), 0)
                total_ews = _to_int(category.get("ews"), 0)

                religion = data.get("religion", {}) or {}
                total_hindu = _to_int(religion.get("hindu"), 0)
                total_muslim = _to_int(religion.get("muslim"), 0)
                total_sikh = _to_int(religion.get("sikh"), 0)
                total_christian = _to_int(religion.get("christian"), 0)
                total_jain = _to_int(religion.get("jain"), 0)
                total_buddhist = _to_int(religion.get("buddhist"), 0)
                total_other_religion = _to_int(religion.get("other"), 0)

                dis = data.get("disability", {}) or {}
                total_no_disability = _to_int(dis.get("none") or dis.get("no_disability"), 0)
                total_low_vision = _to_int(dis.get("lowvision"), 0)
                total_blindness = _to_int(dis.get("blindness"), 0)
                total_hearing = _to_int(dis.get("hearing"), 0)
                total_locomotor = _to_int(dis.get("locomotor"), 0)
                total_autism = _to_int(dis.get("autism"), 0)
                total_other_disability = _to_int(dis.get("other"), 0)

                try:
                    client_ip = get_client_ip(request)

                    existing = student_aggregate_master.objects.filter(
                        College=college,
                        Program=program_obj,
                        Academic_Year=academic_year,
                        is_deleted=False,
                    ).first()

                    
                    if existing:
                        # 🔁 Update fields
                        existing.total_students = total_students
                        existing.total_male = male
                        existing.total_female = female
                        existing.total_others = others

                        existing.total_open = total_open
                        existing.total_obc = total_obc
                        existing.total_sc = total_sc
                        existing.total_st = total_st
                        existing.total_nt = total_nt
                        existing.total_vjnt = total_vjnt
                        existing.total_ews = total_ews

                        existing.total_hindu = total_hindu
                        existing.total_muslim = total_muslim
                        existing.total_sikh = total_sikh
                        existing.total_christian = total_christian
                        existing.total_jain = total_jain
                        existing.total_buddhist = total_buddhist
                        existing.total_other_religion = total_other_religion

                        existing.total_no_disability = total_no_disability
                        existing.total_low_vision = total_low_vision
                        existing.total_blindness = total_blindness
                        existing.total_hearing = total_hearing
                        existing.total_locomotor = total_locomotor
                        existing.total_autism = total_autism
                        existing.total_other_disability = total_other_disability

                        existing.updated_by = client_ip
                        existing.save()

                        updated.append({"program": program_name, "id": existing.pk, "updated": True})
                    else:
                         # 🆕 No existing row → CREATE a new one (for new program/year combo)
                        obj = student_aggregate_master.objects.create(
                            College=college,
                            Program=program_obj,
                            Academic_Year=academic_year,
                            is_deleted=False,
                            created_by=client_ip,
                            total_students=total_students,
                            total_male=male,
                            total_female=female,
                            total_others=others,
                            total_open=total_open,
                            total_obc=total_obc,
                            total_sc=total_sc,
                            total_st=total_st,
                            total_nt=total_nt,
                            total_vjnt=total_vjnt,
                            total_ews=total_ews,
                            total_hindu=total_hindu,
                            total_muslim=total_muslim,
                            total_sikh=total_sikh,
                            total_christian=total_christian,
                            total_jain=total_jain,
                            total_buddhist=total_buddhist,
                            total_other_religion=total_other_religion,
                            total_no_disability=total_no_disability,
                            total_low_vision=total_low_vision,
                            total_blindness=total_blindness,
                            total_hearing=total_hearing,
                            total_locomotor=total_locomotor,
                            total_autism=total_autism,
                            total_other_disability=total_other_disability,
                        )
                        created.append({"program": program_name, "id": obj.pk, "created": True})

                except Exception as e:
                    errors.append({"program": program_name, "error": f"DB error: {str(e)}"})
                    continue

        response_status = 200 if not errors else 207
        resp = {
            "status": response_status,
            "updated": updated,
            "errors": errors,
            "summary": {
                "created": 0,
                "updated": sum(1 for u in updated if u.get("updated")),
                "failed": len(errors)
            }
        }
        return JsonResponse(resp)

    
@ajax_login_required
def get_student_records(request):
    try:
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
    except ValueError:
        return HttpResponseBadRequest("Invalid paging parameters")

    search_value = request.GET.get("search[value]", "").strip()
    order_col_index = request.GET.get("order[0][column]")
    order_dir = request.GET.get("order[0][dir]", "asc")
    year = request.GET.get("year")

    if not year:
        latest = academic_year.objects.order_by("-Academic_Year").first()
        year = latest.Academic_Year if latest else ""

    colleges_qs = College.objects.filter(
        is_deleted=False,
        student_aggregates__Academic_Year=year,
        student_aggregates__is_deleted=False
    ).distinct()

    if search_value:
        colleges_qs = colleges_qs.filter(
            Q(College_Code__icontains=search_value) |
            Q(College_Name__icontains=search_value)
        )

    records_total = colleges_qs.count()
    records_filtered = records_total

    order_map = {
        "1": "College_Code",
        "2": "College_Name",
    }

    if order_col_index == "4":
        colleges_qs = colleges_qs.annotate(
            agg_total=Sum("student_aggregates__total_students",
                          filter=Q(student_aggregates__Academic_Year=year))
        )
        field = "agg_total"
        if order_dir == "desc":
            field = "-" + field
        colleges_qs = colleges_qs.order_by(field, "College_Name")
    else:
        field = order_map.get(order_col_index, "College_Name")
        if order_dir == "desc":
            field = "-" + field
        colleges_qs = colleges_qs.order_by(field)

    colleges_page = colleges_qs[start:start + length]

    data = []

    for col in colleges_page:
        pc_qs = (
            student_aggregate_master.objects
            .filter(College=col, Academic_Year=year, is_deleted=False)
            .select_related("Program")
            .order_by("Program__Discipline", "Program__ProgramName")   # <--- global alphabetical sort
        )

        discipline_map = {}
        total_students_for_college = 0

        for pc in pc_qs:
            prog_obj = pc.Program
            discipline = prog_obj.Discipline if prog_obj else "Unspecified"
            program_name = prog_obj.ProgramName if prog_obj else str(pc.Program_id)

            total_students_for_college += (pc.total_students or 0)

            entry = {
                "name": program_name,
                "total_students": pc.total_students or 0,
                "gender": {
                    "male": pc.total_male or 0,
                    "female": pc.total_female or 0,
                    "others": pc.total_others or 0,
                },
                "category": {
                    "open": pc.total_open or 0,
                    "obc": pc.total_obc or 0,
                    "sc": pc.total_sc or 0,
                    "st": pc.total_st or 0,
                    "nt": pc.total_nt or 0,
                    "vjnt": pc.total_vjnt or 0,
                    "ews": pc.total_ews or 0,
                },
                "religion": {
                    "hindu": pc.total_hindu or 0,
                    "muslim": pc.total_muslim or 0,
                    "sikh": pc.total_sikh or 0,
                    "christian": pc.total_christian or 0,
                    "jain": pc.total_jain or 0,
                    "buddhist": pc.total_buddhist or 0,
                    "other": pc.total_other_religion or 0,
                },
                "disability": {
                    "none": pc.total_no_disability or 0,
                    "lowvision": pc.total_low_vision or 0,
                    "blindness": pc.total_blindness or 0,
                    "hearing": pc.total_hearing or 0,
                    "locomotor": pc.total_locomotor or 0,
                    "autism": pc.total_autism or 0,
                    "other": pc.total_other_disability or 0,
                }
            }

            discipline_map.setdefault(discipline, []).append(entry)

        grouped_list = []
        for disc in sorted(discipline_map.keys(), key=str.lower):
            grouped_list.append({
                "discipline": disc,
                "programs": sorted(discipline_map[disc], key=lambda x: x["name"].lower())
            })

        data.append({
            "college_code": col.College_Code,
            "college_name": col.College_Name,
            "academic_year": year,
            "total_students": total_students_for_college,
            "programs": grouped_list
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })



@ajax_login_required
def delete_student_record(request):
    if request.method == 'POST':
        college_code = request.POST.get('college_code')
        print(college_code)
        academic_year = request.POST.get('academic_year')
        print(academic_year)

        try:
            college = College.objects.get(College_Code=college_code, is_deleted=False)
        except College.DoesNotExist:
            return JsonResponse({'status': 404, 'message': 'College not found'})

        student_aggregate_master.objects.filter(College=college, Academic_Year=academic_year, is_deleted=False).update(is_deleted=True)

        response_data = {
            'message': 'Student records deleted successfully',
            'status': 204
        }
        return JsonResponse(response_data)
    
def get_college_records(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    total_count = College.objects.filter(is_deleted=False).count()

    program_prefetch = Prefetch(
        'college_programs',
        queryset=CollegeProgram.objects.filter(is_deleted=False),
        to_attr='program_list'
    )
    qs = College.objects.filter(is_deleted=False)

    if search_value:
        qs = qs.filter(
            Q(College_Code__icontains=search_value) |
            Q(College_Name__icontains=search_value) |
            Q(address__icontains=search_value) |
            Q(country__icontains=search_value) |
            Q(state__icontains=search_value) |
            Q(District__icontains=search_value) |
            Q(taluka__icontains=search_value) |
            Q(city__icontains=search_value) |
            Q(pincode__icontains=search_value) |
            Q(college_type__icontains=search_value) |
            Q(belongs_to__icontains=search_value) |
            Q(affiliated__icontains=search_value) |
            Q(college_programs__Discipline__icontains=search_value) |
            Q(college_programs__ProgramName__icontains=search_value)
        ).distinct()

    qs = qs.prefetch_related(program_prefetch)
    filtered_count = qs.count()

    # ordering (optional - keep simple)
    column_index = int(request.GET.get('order[0][column]', 2))
    direction = request.GET.get('order[0][dir]', 'asc')
    column_map = {
        1: 'College_Code',
        2: 'College_Name',
        3: 'state',
        4: 'District',
        5: 'city'
    }
    order_field = column_map.get(column_index, 'College_Name')
    if direction == 'desc':
        order_field = '-' + order_field
    qs = qs.order_by(order_field)

    # pagination
    qs_page = qs[start:start + length]

    # Build response rows as objects (so JS can access by property)
    data = []
    for college in qs_page:
        # build programs grouped by discipline
        programs_map = {}
        for p in getattr(college, 'program_list', []):
            programs_map.setdefault(p.Discipline or "Other", []).append(p.ProgramName)

        row = {
            "college_code": college.College_Code,
            "college_name": college.College_Name,
            "address": college.address,
            "country": college.country if hasattr(college, "country") else "",
            "state": college.state,
            "district": college.District,
            "taluka": college.taluka,
            "city": college.city,
            "pincode": college.pincode,
            "college_type": college.college_type,
            "belongs_to": college.belongs_to,
            "affiliated": college.affiliated if hasattr(college, "affiliated") else "",
            "programs": programs_map,
            "id": college.id
        }
        data.append(row)

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_count,
        "recordsFiltered": filtered_count,
        "data": data
    })

@ajax_login_required
def export_colleges_excel(request):

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "College Records"

    # ========= HEADER ==========
    headers = [
        "College Code", "College Name", "Address", "Pincode", "Country",
        "State", "District", "Taluka", "City",
        "College Type", "Belongs To", "Affiliated To",
        "Discipline", "Program"
    ]
    ws.append(headers)

    # Style header
    header_fill = PatternFill(start_color="006699", end_color="006699", fill_type="solid")
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_num = 2  # start from row 2

    colleges = College.objects.filter(is_deleted=False).prefetch_related("college_programs")

    for college in colleges:

        # Group programs under each discipline
        discipline_map = {}
        for cp in college.college_programs.all():
            discipline_map.setdefault(cp.Discipline, []).append(cp.ProgramName)

        if not discipline_map:
            discipline_map = {"No Discipline": ["No Programs"]}

        discipline_list = list(discipline_map.items())

        # Total rows needed = sum of all programs across all disciplines
        total_program_rows = sum(len(programs) for _, programs in discipline_list)

        start_row = row_num
        end_row = row_num + total_program_rows - 1

        # ========== MERGE ALL COLLEGE INFO CELLS ==========
        college_fields = [
            college.College_Code,
            college.College_Name,
            college.address,
            college.pincode,
            college.country,
            college.state,
            college.District,
            college.taluka,
            college.city,
            college.college_type,
            college.belongs_to,
            college.affiliated,
        ]

        for col_index, value in enumerate(college_fields, start=1):
            ws.merge_cells(
                start_row=start_row, start_column=col_index,
                end_row=end_row, end_column=col_index
            )
            cell = ws.cell(row=start_row, column=col_index, value=value)
            cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

        # ========== WRITE DISCIPLINE + PROGRAM CELLS ==========
        current_row = row_num

        for discipline, programs in discipline_list:

            discipline_rowspan = len(programs)
            discipline_start_row = current_row
            discipline_end_row = current_row + discipline_rowspan - 1

            # Merge discipline cell
            ws.merge_cells(
                start_row=discipline_start_row, start_column=13,
                end_row=discipline_end_row, end_column=13
            )
            disc_cell = ws.cell(row=discipline_start_row, column=13, value=discipline)
            disc_cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

            # Write each program in its own row
            for p in programs:
                prog_cell = ws.cell(current_row, 14, p)
                prog_cell.alignment = Alignment(vertical="center", horizontal="left", wrap_text=True)
                current_row += 1

        # Move pointer after writing all rows for this college
        row_num = end_row + 1

    # Auto column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 20

    # ========= RETURN FILE ==========
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="College_Detailed_Report.xlsx"'
    wb.save(response)
    return response

@ajax_login_required
def export_student_excel(request):
    year = request.GET.get("year")
    if not year:
        return HttpResponse("Missing academic year", status=400)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Records"

    # ============================
    #   HEADER ROW
    # ============================
    headers = [
        "College Code", "College Name", "Address", "Pincode", "Country",
        "State", "District", "Taluka", "City",
        "College Type", "Belongs To", "Affiliated To",
        "Discipline", "Program",

        # STUDENT CENSUS COLUMNS (index 14 onward)
        "Total Students",
        "Male", "Female", "Others",
        "OPEN", "OBC", "SC", "ST", "NT", "VJNT", "EWS",
        "Hindu", "Muslim", "Sikh", "Christian", "Jain", "Buddhist", "Other Religion",
        "No Disability", "Low Vision", "Blindness", "Hearing Impaired",
        "Locomotor Disability", "Autism", "Other Disability"
    ]

    ws.append(headers)

    # Header styling
    header_fill = PatternFill(start_color="006699", end_color="006699", fill_type="solid")
    for col in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=col)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center")

    row_num = 2

    # ============================
    #   FETCH ALL NECESSARY DATA
    # ============================
    colleges = (
        College.objects.filter(is_deleted=False)
        .prefetch_related("college_programs", "student_aggregates")
    )

    # student fields order used for writing and aggregation
    student_fields = [
        "total_students",
        "total_male", "total_female", "total_others",
        "total_open", "total_obc", "total_sc", "total_st", "total_nt", "total_vjnt", "total_ews",
        "total_hindu", "total_muslim", "total_sikh", "total_christian", "total_jain", "total_buddhist", "total_other_religion",
        "total_no_disability", "total_low_vision", "total_blindness", "total_hearing",
        "total_locomotor", "total_autism", "total_other_disability"
    ]

    for college in colleges:

        # map program_id -> student_aggregate record for the given year
        year_records = {
            r.Program_id: r
            for r in college.student_aggregates.filter(Academic_Year=year, is_deleted=False)
        }

        # Group programs by discipline (only non-deleted programs)
        discipline_map = {}
        for cp in college.college_programs.filter(is_deleted=False):
            discipline_map.setdefault(cp.Discipline, []).append(cp)

        # if no disciplines/programs exist, show a placeholder discipline with no programs
        if not discipline_map:
            discipline_map = {"No Discipline": []}

        # compute total rows needed for the college (sum of program counts, at least 1 per discipline)
        total_program_rows = 0
        for disc, plist in discipline_map.items():
            if plist:
                total_program_rows += len(plist)
            else:
                total_program_rows += 1  # one row to show 'No Program'

        start_row = row_num
        end_row = row_num + total_program_rows - 1

        # ============================
        #   MERGE COLLEGE INFO CELLS OVER THE FULL BLOCK
        # ============================
        college_fields = [
            college.College_Code,
            college.College_Name,
            college.address,
            college.pincode,
            college.country,
            college.state,
            college.District,
            college.taluka,
            college.city,
            college.college_type,
            college.belongs_to,
            college.affiliated
        ]

        for col_index, value in enumerate(college_fields, start=1):
            ws.merge_cells(start_row=start_row, start_column=col_index,
                           end_row=end_row, end_column=col_index)
            c = ws.cell(row=start_row, column=col_index, value=value)
            c.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

        # ============================
        #   WRITE DISCIPLINE (rowspan) AND PROGRAM ROWS
        #   Also build per-college aggregate sums for student census
        # ============================
        current_row = row_num
        # initialize aggregate counters to zero
        agg = {f: 0 for f in student_fields}

        for discipline, program_list in discipline_map.items():
            # ensure at least one program row (placeholder if empty)
            programs = program_list if program_list else [None]
            discipline_rowspan = len(programs)
            discipline_start = current_row
            discipline_end = current_row + discipline_rowspan - 1

            # merge the discipline cell for its rowspan
            ws.merge_cells(start_row=discipline_start, start_column=13,
                           end_row=discipline_end, end_column=13)
            disc_cell = ws.cell(row=discipline_start, column=13, value=discipline)
            disc_cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)

            # write each program row
            for prog in programs:
                # program name or placeholder
                if prog:
                    ws.cell(current_row, 14, prog.ProgramName)
                    record = year_records.get(prog.id)
                else:
                    ws.cell(current_row, 14, "No Program")
                    record = None

                # write student census values starting at column 15
                if record:
                    for i, field in enumerate(student_fields):
                        val = getattr(record, field, 0) or 0
                        ws.cell(current_row, 15 + i, val)
                        agg[field] += val
                else:
                    # write zeros or dashes (choose zeros to make aggregation easier)
                    for i, field in enumerate(student_fields):
                        ws.cell(current_row, 15 + i, 0)

                current_row += 1

        # ============================
        #   AGGREGATE ROW — sums for this college
        # ============================
        agg_row = current_row
        # Merge the left columns (1..14) for label cell
        ws.merge_cells(start_row=agg_row, start_column=1, end_row=agg_row, end_column=14)
        label_cell = ws.cell(agg_row, 1, "Aggregate Value")
        label_cell.font = Font(bold=True)
        label_cell.alignment = Alignment(horizontal="center", vertical="center")

        # write aggregated totals starting at column 15
        for i, field in enumerate(student_fields):
            tot = agg[field]
            cell = ws.cell(agg_row, 15 + i, tot)
            cell.font = Font(bold=True, color="CC6600")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # move pointer to next row after this block
        row_num = agg_row + 1

    # Auto column width
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18

    # RESPONSE
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="Student_Report_{year}.xlsx"'
    wb.save(response)
    return response

