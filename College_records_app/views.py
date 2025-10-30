from django.shortcuts import render
from .models import College, CollegeProgram, Taluka, District, Discipline, Programs, CollegeType, BelongsTo
from django.db.models import Prefetch
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from functools import wraps
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


def home(request):
    return render(request, 'index.html', {"Colleges": College.objects.filter(is_deleted = False), "disciplines" : Discipline.objects.all(), "Collegetype" : CollegeType.objects.all(), "BelongsTo": BelongsTo.objects.all(), "programs":Programs.objects.all()})  # Make sure 'index.html' exists in templates
   

def college_master(request):
    return render(request, 'college_master.html', {"disciplines" : Discipline.objects.all(), "Collegetype" : CollegeType.objects.all(), "BelongsTo": BelongsTo.objects.all()})  # Make sure 'tables.html' exists in templates


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
                'message': 'record updated successfully',
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
                'message': 'record added successfully',
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
            'total_colleges_count' : College.objects.filter(is_deleted = False).count()
        }
        print(response_data)
    else:
        response_data = {
            'is_authenticated' : False,
            'status' : 401
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


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username = username).exists():
            response_data = {
                'message' : 'username already exists',
                'status' : 400
            }
            return JsonResponse(response_data)
        
        if User.objects.filter(email = email).exists():
            print("inside")
            response_data = {
                'message' : 'email already exists',
                'status' : 400
            }
            return JsonResponse(response_data)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        response_data = {
            'message' : 'user created successfully',
            'status' : 201
        }
        return JsonResponse(response_data)
    

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me', '0')
        username = User.objects.get(email=email).username

        user = authenticate(request, username = username, password = password)

        if user is not None:
            login(request, user)
            if remember_me == '1':
                request.session.set_expiry(86400)  # 24 hrs
            response_data = {
                'message' : 'login successful',
                'status' : 200,
                'username' : username,
                'total_colleges_count' : College.objects.filter(is_deleted = False).count()
            }

            return JsonResponse(response_data)
        else:
            response_data = {
                'message' : 'invalid credentials',
                'status' : 401
            }
            return JsonResponse(response_data)
        
        
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