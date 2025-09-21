from django.shortcuts import render
from .models import Colleges
from django.db.models import Q
from django.http import JsonResponse
# Create your views here.

def get_client_ip(request):
    """Get the real client IP address from request headers"""
    x_forwarded_for = request.META.get(('HTTP_X_FORWARDED_FOR'))
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip

def home(request):
    return render(request, 'index.html')


def get_records(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    TotalRecord = 0
    FilteredRecord = 0
    data = []

    TotalRecord = Colleges.objects.filter(is_deleted = False).count()

    # searching
    if search_value:
        college_queryset = Colleges.objects.filter((Q(College_Code__icontains = search_value)|Q(College_Name__icontains = search_value)|Q(address__icontains = search_value)|Q(country__icontains = search_value)|Q(state__icontains = search_value)|Q(District__icontains = search_value)|Q(taluka__icontains = search_value)|Q(city__icontains = search_value)|Q(college_type__icontains = search_value)|Q(belongs_to__icontains = search_value)|Q(affiliated__icontains = search_value)|Q(discipline__icontains = search_value))&Q(is_deleted = False))
    else:
        college_queryset = Colleges.objects.filter(is_deleted = False)
    
    # Filtered record count
    FilteredRecord = college_queryset.count()

    #sorting
    column_index = int(request.GET.get('order[0][column]', 0))
    direction = request.GET.get('order[0][dir]', 'asc')

    column_name = ['College_Code', 'College_Name','address','country','state','District','taluka','city','college_type','belongs_to','affiliated','discipline'] [column_index]

    if direction == 'desc':
        column_name = f'-{column_name}'
    
    college_queryset = college_queryset.order_by(column_name)


    # pagination

    college_queryset = college_queryset[start:start+length]

    for college in college_queryset:
        data.append([college.College_Code, college.College_Name, college.address, college.country ,college.state, college.District, college.taluka, college.city,college.college_type, college.belongs_to, college.affiliated,  college.discipline.replace(",", ", "), college.id])

    
    response = {
        'draw' : draw,
        'recordsTotal' : TotalRecord,
        'recordsFiltered' : FilteredRecord,
        'data' : data
    }

    return JsonResponse(response)



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
        college_type = request.POST.get('college_type')
        belongs_to = request.POST.get('belongs_to')
        affiliated = request.POST.get('affiliated_to')
        discipline_list = request.POST.getlist('discipline[]')
        discipline = ",".join(discipline_list) 

        client_ip = get_client_ip(request)

        if id == 0:
            college = Colleges.objects.create(
                College_Code = college_code,
                College_Name = college_name,
                address = address,
                country = country,
                state = state,
                District = district,
                taluka = taluka,
                city = city,
                college_type = college_type,
                belongs_to = belongs_to,
                affiliated = affiliated,
                discipline = discipline,
                created_by = client_ip
            )

            response_data = {
                'message' : "record created successfully",
                'status' : 201
            }

            return JsonResponse(response_data)
        
        else:
            college = Colleges.objects.get(id = id)
            college.College_Code = college_code
            college.College_Name = college_name
            college.address = address
            college.country = country
            college.state = state
            college.District = district
            college.taluka = taluka
            college.city = city
            college.college_type = college_type
            college.belongs_to = belongs_to
            college.affiliated = affiliated
            college.discipline = discipline
            college.updated_by = client_ip

            college.save()

            response_data = {
                'message' : "record updated successfully",
                'status' : 200
            }

            return JsonResponse(response_data)


def delete_record(request):
    if request.method == 'POST':
        id = request.POST.get('id')
        record = Colleges.objects.get(id = id)
        record.is_deleted = True
        record.save()

        response_data = {
            'message' : 'record deleted successfully',
            'status' : 204
        }
        return JsonResponse(response_data)

