from django.shortcuts import render, redirect
from .models import College, CollegeProgram, Taluka, District, Discipline, Programs, CollegeType, BelongsTo, academic_year, student_aggregate_master
from django.db.models import Prefetch
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from functools import wraps
from django.db import transaction
import json
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


def get_records(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    TotalRecord = College.objects.filter(is_deleted=False).count()

    program_prefetch = Prefetch(
        'college_programs',
        queryset=CollegeProgram.objects.filter(is_deleted=False),
        to_attr='program_list'
    )

    college_queryset = College.objects.filter(is_deleted=False)

    if search_value:
        college_queryset = college_queryset.filter(
            Q(College_Code__icontains=search_value)
            | Q(College_Name__icontains=search_value)
            | Q(address__icontains=search_value)
            | Q(country__icontains=search_value)
            | Q(state__icontains=search_value)
            | Q(District__icontains=search_value)
            | Q(taluka__icontains=search_value)
            | Q(city__icontains=search_value)
            | Q(pincode__icontains=search_value)
            | Q(college_type__icontains=search_value)
            | Q(belongs_to__icontains=search_value)
            | Q(affiliated__icontains=search_value)
            | Q(college_programs__Discipline__icontains=search_value)
            | Q(college_programs__ProgramName__icontains=search_value)
        ).distinct()

    college_queryset = college_queryset.prefetch_related(program_prefetch)
    FilteredRecord = college_queryset.count()

    # Sorting
    column_index = int(request.GET.get('order[0][column]', 0))
    direction = request.GET.get('order[0][dir]', 'asc')
    column_map = [
        'College_Code', 'College_Name', 'address', 'country', 'state',
        'District', 'taluka', 'city', 'pincode', 'college_type',
        'belongs_to', 'affiliated'
    ]
    column_name = column_map[column_index] if column_index < len(column_map) else 'College_Code'
    if direction == 'desc':
        column_name = f'-{column_name}'
    college_queryset = college_queryset.order_by(column_name)

    # Pagination
    college_queryset = college_queryset[start:start + length]

    data = []

    for college in college_queryset:
        disciplines_map = {}

        for prog in getattr(college, 'program_list', []):
            disciplines_map.setdefault(prog.Discipline, []).append(prog.ProgramName)

        first_row = True
        for discipline, programs in disciplines_map.items():
            data.append([
                college.College_Code if first_row else "",
                college.College_Name if first_row else "",
                college.address if first_row else "",
                college.country if first_row else "",
                college.state if first_row else "",
                college.District if first_row else "",
                college.taluka if first_row else "",
                college.city if first_row else "",
                college.pincode if first_row else "",
                college.college_type if first_row else "",
                college.belongs_to if first_row else "",
                college.affiliated if first_row else "",
                discipline,
                ", ".join(programs),
                college.id if first_row else "",  # visible action cell
                college.id  # hidden group key (NEW)
            ])
            first_row = False

    response = {
        'draw': draw,
        'recordsTotal': TotalRecord,
        'recordsFiltered': FilteredRecord,
        'data': data
    }
    return JsonResponse(response)


@ajax_login_required
def add_edit_record(request):
    if request.method == "POST":
        id = int(request.POST.get('id'))
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
        disciplines_programs_json = request.POST.get('disciplines_programs')

        disciplines_programs = json.loads(disciplines_programs_json)

        if id > 0:
            # Edit existing record
            college = College.objects.get(id=id)
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

            # Update CollegeProgram entries
            CollegeProgram.objects.filter(College=college).update(is_deleted=True)
            for item in disciplines_programs:
                discipline = item['Discipline']
                program_name = item['ProgramName']
                cp, created = CollegeProgram.objects.get_or_create(
                    College=college,
                    Discipline=discipline,
                    ProgramName=program_name,
                    defaults={'is_deleted': False}
                )
                if not created:
                    cp.is_deleted = False
                    cp.save()

            response_data = {
                'message': 'Record updated successfully',
                'status': 200
            }
            return JsonResponse(response_data)
        else:
            # Add new record
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
            for item in disciplines_programs:
                discipline = item['Discipline']
                program_name = item['ProgramName']
                CollegeProgram.objects.create(
                    College=college,
                    Discipline=discipline,
                    ProgramName=program_name
                )
            response_data = {
                'message': 'Record added successfully',
                'status': 201
            }
            return JsonResponse(response_data)


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
            'total_students_count' : student_aggregate_master.objects.filter(College__is_deleted = False).aggregate(total=Sum('total_students'))['total'] or 0
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

        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            return JsonResponse({'status': 401, 'message': 'Invalid email or password'})

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
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
        
        if disciplines:
            discipline_query = Q()
            for discipline in disciplines:
                discipline_query |= Q(college_programs__Discipline__icontains = discipline)
            filter_criteria &= discipline_query
        if programs:
            program_query = Q()
            for program in programs:
                program_query |= Q(college_programs__ProgramName__icontains = program)
            filter_criteria &= program_query
        


        filtered_colleges_count = College.objects.filter(filter_criteria).distinct().count()
        print("Filtered count:", filtered_colleges_count)
        
        response_data = {
            'message' : 'filters applied successfully',
            'status' : 200,
            'count_data' : filtered_colleges_count
        }

        return JsonResponse(response_data)
    

def clear_filters(request):
    if request.method == "GET":
        response_data = {
            'status' : 200,
            'total_colleges_count' : College.objects.filter(is_deleted = False).count()
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

    # Programs list
    programs = CollegeProgram.objects.filter(
        College=college, is_deleted=False
    ).values_list("ProgramName", flat=True)

    # Full address exactly like before
    full_address = f"{college.address}, {college.taluka}, {college.District} - {college.pincode}"

    base_college_data = {
        "College_Code": college.College_Code,
        "College_Name": college.College_Name,
        "address": full_address,
        "District": college.District,
        "Taluka": college.taluka,
        "pincode": college.pincode,
        "programs": list(programs)
    }

    # ---------------------------------------------------------
    # ADD MODE
    # ---------------------------------------------------------
    if mode == "add":

        return JsonResponse({
            "status": 200,
            "mode": "add",
            "academic_year": academic_year,   # <-- IMPORTANT
            "college_data": base_college_data,
            "records": {}                     # empty for add mode
        })

    # ---------------------------------------------------------
    # EDIT MODE
    # ---------------------------------------------------------
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
            filled_records[agg.Program.ProgramName] = {
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


def add_edit_student_aggregate(request):
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

        # We'll do everything in a transaction so you get all-or-nothing.
        # If you prefer partial saves, remove the transaction.atomic block.
        with transaction.atomic():
            for program_name, data in records.items():
                program_obj = CollegeProgram.objects.filter(College=college, ProgramName=program_name,is_deleted=False).first()
                
                if not program_obj:
                    errors.append(f"Program '{program_name}' not found for college '{college_code}'")
                    continue
                
                # --- parse numeric fields safe ---
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
                    obj, created = student_aggregate_master.objects.update_or_create(
                        College=college,
                        Program=program_obj,
                        Academic_Year=academic_year,
                        defaults=defaults
                    )
                    if  created:
                        obj.created_by = get_client_ip(request)
                        obj.save(update_fields=["created_by"])
                    if not created:
                        obj.updated_by = get_client_ip(request)
                        obj.save(update_fields=["updated_by"])



                    saved.append({"program": program_name, "id": obj.pk, "created": created})
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
                "updated": sum(1 for s in saved if not s.get("created")),
                "failed": len(errors)
            }
        }
        return JsonResponse(resp)
    

def get_student_records(request):
    """
    Server-side DataTables endpoint.
    One row per college (that has student_aggregate_master entries for the selected year).
    Each row includes `programs` array (per-program census).
    """
    try:
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
    except ValueError:
        return HttpResponseBadRequest("Invalid paging parameters")

    search_value = request.GET.get("search[value]", "").strip()
    order_col_index = request.GET.get("order[0][column]")
    order_dir = request.GET.get("order[0][dir]", "asc")
    year = request.GET.get("year", None)  # must be provided by frontend

    if not year:
        # default to latest if not provided
        latest = academic_year.objects.order_by("-Academic_Year").first()
        year = latest.Academic_Year if latest else ""

    # base: colleges that have aggregates for this year and not deleted
    colleges_qs = College.objects.filter(is_deleted=False, student_aggregates__Academic_Year=year).distinct()

    # Search filter
    if search_value:
        colleges_qs = colleges_qs.filter(
            Q(College_Code__icontains=search_value) | Q(College_Name__icontains=search_value)
        )

    records_total = colleges_qs.count()
    records_filtered = records_total  # after search (already applied)

    # Simple ordering mapping:
    # 0 = Action (ignore), 1 = College Code, 2 = College Name, 3 = Academic Year, 4 = Total Students
    order_map = {
        "1": "College_Code",
        "2": "College_Name",
        # total_students (4) we will order manually by annotating
    }

    # If ordering by total_students (column index 4), we annotate sums and order accordingly
    order_by_annotation = None
    if order_col_index == "4":
        # annotate total_students per college for the requested year and order
        # annotate using related_name student_aggregates
        colleges_qs = colleges_qs.annotate(
            agg_total=Sum('student_aggregates__total_students', filter=Q(student_aggregates__Academic_Year=year))
        )
        order_by_annotation = "agg_total"
        if order_dir == "desc":
            order_by_annotation = "-" + order_by_annotation
        colleges_qs = colleges_qs.order_by(order_by_annotation, "College_Name")
    else:
        order_field = order_map.get(order_col_index, "College_Name")
        if order_dir == "desc":
            order_field = "-" + order_field
        colleges_qs = colleges_qs.order_by(order_field)

    # pagination (slice)
    colleges_page = colleges_qs[start:start + length]

    data = []
    # Build row per college (with programs for the year)
    for col in colleges_page:
        # fetch program aggregates for this college and year
        pc_qs = student_aggregate_master.objects.filter(College=col, Academic_Year=year, is_deleted=False).select_related("Program")
        programs = []
        total_students_for_college = 0
        for pc in pc_qs:
            # map DB fields into structures
            prog = {
                "name": pc.Program.ProgramName if pc.Program else str(pc.Program_id),
                "total_students": pc.total_students or 0,
                "gender": {
                    "male": pc.total_male or 0,
                    "female": pc.total_female or 0,
                    "others": pc.total_others or 0
                },
                "category": {
                    "open": pc.total_open or 0,
                    "obc": pc.total_obc or 0,
                    "sc": pc.total_sc or 0,
                    "st": pc.total_st or 0,
                    "nt": pc.total_nt or 0,
                    "vjnt": pc.total_vjnt or 0,
                    "ews": pc.total_ews or 0
                },
                "religion": {
                    "hindu": pc.total_hindu or 0,
                    "muslim": pc.total_muslim or 0,
                    "sikh": pc.total_sikh or 0,
                    "christian": pc.total_christian or 0,
                    "jain": pc.total_jain or 0,
                    "buddhist": pc.total_buddhist or 0,
                    "other": pc.total_other_religion or 0
                },
                "disability": {
                    "none": pc.total_no_disability or 0,
                    "lowvision": pc.total_low_vision or 0,
                    "blindness": pc.total_blindness or 0,
                    "hearing": pc.total_hearing or 0,
                    "locomotor": pc.total_locomotor or 0,
                    "autism": pc.total_autism or 0,
                    "other": pc.total_other_disability or 0
                }
            }
            programs.append(prog)
            total_students_for_college += (pc.total_students or 0)

        data.append({
            "college_code": col.College_Code,
            "college_name": col.College_Name,
            "academic_year": year,
            "total_students": total_students_for_college,
            "programs": programs
        })

    resp = {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    }
    return JsonResponse(resp)

def delete_student_record(request):
    pass
    