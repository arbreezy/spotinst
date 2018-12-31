#!/usr/bin/env python
import spotinst_sdk
import sys
import argparse
import netrc
import re
'''
Python script to manage spotinst API calls
having a basic control over our Elastigroups
'''

def yes_no(answer):
    '''
    Dead simple yes/no question
    '''
    yes = set(['yes','y', 'ye', ''])
    no = set(['no','n'])
     
    while True:
        choice = raw_input(answer).lower()
        if choice in yes:
           return True
        elif choice in no:
           return False
        else:
           print ("Please respond with 'yes' or 'no'\n")

def validate_gid(id):
    '''
    Validate that the given group ID is in the right form
    '''
    pattern = re.compile('^sig-[a-zA-Z0-9]+$')
    matching = pattern.match(id)
    is_matching =  bool(matching)
    return is_matching


def update_capac(id,cmin,cmax,target,client_obj):
    '''
    Update capacity attributes
    ''' 
    capacity_update = spotinst_sdk.aws_elastigroup.Capacity(minimum=cmin,maximum=cmax,target=target)
    group_update = spotinst_sdk.aws_elastigroup.Elastigroup(capacity=capacity_update)
    apply_update = client_obj.update_elastigroup(group_update=group_update, group_id=id)

def deploy(id,batch_size,grace_per,client_obj):
    '''
    Roll new instances
    '''
    matching = validate_gid(id)
    if len(id) == 12 and matching:
        group_roll = spotinst_sdk.aws_elastigroup.Roll(batch_size_percentage=batch_size,grace_period=grace_per)
        roll_response = client_obj.roll_group(group_id=id, group_roll=group_roll)
        return roll_response
    else:
        print ("\n[ERROR] Wrong Elastigroup id, try again. Exiting..\n")
        sys.exit(1)


def scaleup(client_obj, id, adj):
    '''
    Scale up based on the given adjustment for a certain
    Elastigroup.
    '''
    matching = validate_gid(id)
    if len(id) == 12 and matching:
       result = client_obj.scale_elastigroup_up(group_id=id, adjustment=adj)
       print (result)

def scaledown(client_obj,id, adj):
    '''
    Scale down based on the given adjustment for a certain
    Elastigroup
    '''
    matching = validate_gid(id)
    if len(id) == 12 and matching:
        client_obj.scale_elastigroup_down(group_id=id, adjustment=adj)
        print (result)

def showid(id,client_obj):
    '''
    Show information about all groups or a specific one
    '''
    matching = validate_gid(id)
    if id == 'all':
        all_groups = client_obj.get_elastigroups()
        for group in all_groups:
            cap_target = group['capacity'].get('target')
            cap_min = group['capacity'].get('minimum')
            cap_max = group['capacity'].get('maximum')
            print ("%s : %s  with min:%s max:%s target:%s" %(group['id'],group['name'],cap_min,cap_max,cap_target)) 
    elif len(id) == 12  and matching:
        result = client_obj.get_elastigroup(group_id=id)
        group_name = result['name']
        env = result['compute'].get('launch_specification').get('tags')[1].get('tag_value')
        ami = result['compute'].get('launch_specification').get('image_id')
        capacity = result['capacity']
        cap_target = result['capacity'].get('target')
        cap_min = result['capacity'].get('minimum')
        cap_max = result['capacity'].get('maximum')
        return capacity,cap_target,cap_min,cap_max,group_name,env,ami
    else:
        print ("\n[ERROR] Wrong Elastigroup id, try again. Exiting..\n")
        sys.exit(1)


def connection(token_type):
    '''
    Initialize connection with Spotinst API
    '''
    try:
        account = netrc.netrc().authenticators(token_type)[0]
        token =  netrc.netrc().authenticators(token_type)[2]

    except:
        netrc.NetrcParseError( "No authenticators for %s" %token_type)
        print ("Can't find .netrc file. Exiting")
        sys.exit(1)
    
    spotinst_client = spotinst_sdk.SpotinstClient(auth_token=token, account_id=account)
    return spotinst_client



def main():
    '''
    Apply functions based on the given arguments.
    '''
    spotinst_parser = argparse.ArgumentParser(
        description='''
        ** Managing Spotinst Elastigroup actions **
        ''',
        epilog='Author: Aris Boutselis  <aristeidis.boutselis@endclothing.com>')
    spotinst_parser.add_argument('--type','-t', action='store', dest='type', required=True,
                       help='Type of the Organization, two possible \
                       values are magento, launches. This argument \
                       is required. e.g spotinst -t magento .')
    spotinst_parser.add_argument('--list','-l', action='store', dest='id',
                       help='Show information about a single or all Elastigroups \
                       of the organization e.g spotinst -t magento --list all.')
    spotinst_parser.add_argument('--scaleup', action='store',dest='uparg',nargs=2,       
                       help='Scale up a number of instances for a given Elastigroup. \
                       Note: we heavily use autoscaling groups, scaling is done based on asg policy. \
                       e.g --scaleup <group_id> <number> .')
    spotinst_parser.add_argument('--scaledown', action='store',dest='downarg',nargs=2,
                       help='Scale down a number of instances for a given \
                       Elastigroup. Note: we heavily use autoscaling groups,\
                       scaling is done based on asg policy. e.g --scaledown <group_id> <number> .')
    spotinst_parser.add_argument('--capacity',action='store',dest='caparg',nargs=4,
                       help= 'Update capacity values for a given Elastigroup. \
                       e.g --capacity <group_id> <min> <max> <target> .')
    spotinst_parser.add_argument('--deploy','-d',action='store',dest='deparg',nargs=3,
                       help= 'Roll new instances in a single Elastigroup. \
                       e.g --deploy <group_id> <batch_percentage> <grace_period>.')
    spotinst_parser.add_argument('--pipelines', action='store',dest='bbpipelines',nargs=2,
                       help= 'Used only inside Bitbucket pipelines. This argument bypasses netrc auth mechanism \
                       e.g --pipelines <spotinst_account> <spotinst_account_token>.')
    spotinst_results = spotinst_parser.parse_args()
    # get the type to extract the appropriate account id and token
    type_values = ['magento','launches']
    #Be sure that token type is specified, --type <launches|magento>
    if spotinst_results.type in type_values and len(sys.argv) > 4:
        # if this script is used in Bitbucket pipelines, will try to
        # authenticate via Bitbucket ENV variables for the account and token values 
        if spotinst_results.bbpipelines:
            account = spotinst_results.bbpipelines[0]
            token = spotinst_results.bbpipelines[1]
            spotinst_client = spotinst_sdk.SpotinstClient(auth_token=token, account_id=account)
        else:
            token_type = spotinst_results.type+'-token'
            spotinst_client =  connection(token_type)

        # --scaleup
        if spotinst_results.uparg:
            if "sig-" in spotinst_results.uparg[0] and len(spotinst_results.uparg[1]) <= 2:
                scaleup(spotinst_client,spotinst_results.uparg[0],spotinst_results.uparg[1])
            else:
                print ("\n[ERROR] Wrong arguments for scale up function.Exiting...\n" ,spotinst_parser.print_help())
                sys.exit(1)
        # --scaledown
        if spotinst_results.downarg:
            if "sig-" in spotinst_results.downarg[0] and len(spotinst_results.downarg[1]) <= 2:
                scaledown(spotinst_client,spotinst_results.downarg[0],spotinst_results.downarg[1])
            else:
                 print ("\n[ERROR] Wrong arguments for scale down function.Exiting...\n",spotinst_parser.print_help()) 
                 sys.exit(1)
        # --capacity X X X X
        if spotinst_results.caparg:
            oldtarget = showid(spotinst_results.caparg[0], spotinst_client)[1]
            oldmin = showid(spotinst_results.caparg[0], spotinst_client)[2]
            oldmax = showid(spotinst_results.caparg[0], spotinst_client)[3]
            print ("Existing Capacity is min: %s, max: %s, target: %s \n"%(oldmin,oldmax,oldtarget))
            cmin = spotinst_results.caparg[1]
            cmax = spotinst_results.caparg[2]
            target = spotinst_results.caparg[3]
            if len(spotinst_results.caparg[1]) <= 2 and \
            len(spotinst_results.caparg[2]) <= 2 and \
            len(spotinst_results.caparg[3]) <= 2:
                print ("\nRequested capacity is min:%s, max:%s, target:%s \n" %(cmin,cmax,target))
                answer = yes_no('Execute the request?\n')
                if answer:
                    update_capac(spotinst_results.caparg[0], cmin, cmax, target, spotinst_client)
                else:
                    print ("\nAborting..")
                    sys.exit(1)
            else:
                print ("\n[ERROR]: Accepted values should be maximum 2 digit length.\n")
 
        # --list all|<group_id>         
        if spotinst_results.id:
            if spotinst_results.id == 'all':
                showid(spotinst_results.id, spotinst_client)
            elif "sig-" in spotinst_results.id :
                capacity,cap_target,cap_min,cap_max,group_name,env,ami = showid(spotinst_results.id, spotinst_client)
                print ("Group name:%s \nEnvironment:%s \nAmi:%s \nCapacity is min:%s, max:%s and target:%s" %(group_name,env,ami,cap_min,cap_max,cap_target))
            else:
                print ("\n[ERROR]: Accepted values should start with sig-xxxxxxxx \n",spotinst_parser.print_help())
                sys.exit(1)

        # --deploy <group_id> <batch_perc> <grace_period>
        if spotinst_results.deparg:
            if "sig-" in spotinst_results.deparg[0] and \
            len(spotinst_results.deparg[1]) <= 3 and \
            len(spotinst_results.deparg[2])  <= 3:
                    print ("\nRequested batch percentage is %s and grace period is %s \n" %(spotinst_results.deparg[1],spotinst_results.deparg[2]))
                    if spotinst_results.bbpipelines:
                        deploy(spotinst_results.deparg[0],spotinst_results.deparg[1],spotinst_results.deparg[2],spotinst_client)
                    else:
                        answer = yes_no('Execute the request?\n')
                        if answer:
                            deploy(spotinst_results.deparg[0],spotinst_results.deparg[1],spotinst_results.deparg[2],spotinst_client)
                        else:
                            print ("\n[ERROR]: Accepted values should start with sig-xxxxxxxx \n" ,spotinst_parser.print_help())
                            sys.exit(1)

    else:
        print ("\n[Error]: Nothing to do. Exiting..\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
