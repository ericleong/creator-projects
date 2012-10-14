# Create your views here.
from dj.models import Test, Choice
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import datetime
import json

def list_choices(choices):
    list_choices = []
    for choice in choices:
        
        list_choices.append({
                             'id' : choice.pk,
                             'image': choice.image.url
                             })
        
    return list_choices

def dict_test(test):
    return {'id' : test.pk, 
            'pub_date' : str(test.pub_date),
            'question' : test.question,
            'choices' : list_choices(test.choices.all())}

def list_tests(tests):
    """Returns a serialized string of the given tests."""
    list_tests = [] # empty list of choices
    for test in tests:
        list_tests.append(dict_test(test))
        
    return list_tests

def serialize_tests(tests):
    return json.dumps(list_tests(tests));

def test(request):
    if request.method == "POST":
        return post_test(request)
    else:
        return get_test(request)

def get_test(request):
    tests = Test.objects.all()
        
    if 'since' in request.GET:
        since = datetime.datetime.strptime(request.GET['since'], '%Y-%m-%d %H:%M:%SZ')
        tests = tests.filter(creation_date__gt=since)
    elif 'since_id' in request.GET:
        since_id = request.GET['since_id']
        tests = tests.filter(pk__gt=since_id)
    
    tests = tests.order_by('pub_date')
        
    offset = int(request.GET.get('offset', '0'))
    limit = int(request.GET.get('limit', '5')) 
    tests = tests[offset : offset + limit]
    
    return HttpResponse(serialize_tests(tests), mimetype="application/json") # Send data back to the user.

@csrf_exempt
def post_test(request):
    """User is submitting a test."""
    
    result = {'status' : 'OK'}
    
    if len(request.FILES.items()) < 2: # make sure we have multiple choices
        result['status'] = 'We need multiple choices!'
        return HttpResponse(json.dumps(result))
    
    test = Test.objects.create(question=request.POST.get('question', ''))
    
    for key, f in request.FILES.items(): #@UnusedVariable
        c = Choice(test=test)
        
        c.image.save(f.name, f, save=True)
        c.save()
        
    result['test'] = dict_test(test)
    
    return HttpResponse(json.dumps(result))

def vote(request):
    if request.method == "POST":
        return post_vote(request)
    else:
        return get_vote(request)

def get_vote(request):
    result = {'status' : 'OK',
              'votes' : json.loads(request.get_signed_cookie('chosen', default='[]'))}
    return HttpResponse(json.dumps(result))

@csrf_exempt
def post_vote(request):
    """User is voting on a test."""
    
    result = {'status' : 'OK'}
    
    if 'choice' not in request.POST: # make sure we have multiple choices
        result['status'] = 'ERROR'
        result['message'] = 'Need to choose to vote!'
        return HttpResponse(json.dumps(result))
    
    chosen = json.loads(request.get_signed_cookie('chosen', default='[]'));
    
    choice_id = request.POST.get('choice')        
    
    try:
        choice = Choice.objects.get(pk=choice_id)
    except Choice.DoesNotExist:
        result['status'] = 'ERROR'
        result['message'] = 'Choice not found.'
        return HttpResponse(json.dumps(result))
    
    if set([choice.id for choice in choice.test.choices.all()]) & set(chosen):
        result['status'] = 'FORBIDDEN'
        result['message'] = 'You voted on this already!'
        return HttpResponse(json.dumps(result))
    
    choice.votes += 1;
    choice.save();
    
    result['id'] = choice.id;
    result['votes'] = choice.votes;
    
    chosen.append(choice.id)
     
    response = HttpResponse(json.dumps(result))
    response.set_signed_cookie('chosen', json.dumps(chosen))
    
    return response