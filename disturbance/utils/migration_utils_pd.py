from ledger.accounts.models import Organisation as ledger_organisation
from ledger.accounts.models import OrganisationAddress
from ledger.accounts.models import EmailUser
from ledger.payments.models import Invoice
from django.conf import settings
from disturbance.components.organisations.models import Organisation, OrganisationContact, UserDelegation
from disturbance.components.main.models import ApplicationType
from disturbance.components.main.utils import get_category
from disturbance.components.proposals.models import Proposal, ProposalType, ApiarySite, ApiarySiteOnProposal, ProposalApiary #, ProposalOtherDetails, ProposalPark
from disturbance.components.approvals.models import Approval, MigratedApiaryLicence, ApiarySiteOnApproval
#from commercialoperator.components.bookings.models import ApplicationFee, ParkBooking, Booking
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError, transaction
from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone
from ledger.address.models import Country
import csv
import os
import datetime
import time
import string
from dateutil.relativedelta import relativedelta
from decimal import Decimal

import logging
logger = logging.getLogger(__name__)

NL = '\n'

COLUMN_MAPPING = {
    'Permit No':              'permit_number',
    'Start Date':             'start_date',
    'Expiry Date':            'expiry_date',
    'Issue Date':             'issue_date',
    'Status':                 'status',
    'Latitude':               'latitude',
    'Longitude':              'logitude',
    'Trading Name':           'trading_name',
    'Licensee':               'licencee',
    'ABN':                    'abn',
    'First Name':             'first_name',
    'Surname':                'last_name',
    'Other Contact':          'other_contact',
    'Address 1':              'address_line1',
    'Address 2':              'address_line2',
    'Address 3':              'address_line3',
    'Suburb':                 'suburb',
    'State':                  'state',
    'Country':                'country',
    'Post':                   'postcode',
    'Telephone1':             'phone_number1',
    'Telephone2':             'phone_number2',
    'Mobile':                 'mobile_number',
    'EMAIL':                  'email',
    'licensed_site':          'licensed_site',
    'batch_no':               'batch_no',
    'approval_cpc_date':      'approval_cpc_date',
    'approval_minister_date': 'approval_minister_date',
    'map_ref':                'map_ref',
    'forest_block':           'forest_block',
    'cog':                    'cog',
    'roadtrack':              'roadtrack',
    'zone':                   'zone',
    'catchment':              'catchment',
    'dra_permit':             'dra_permit',
    'suspended':              'suspended',
}

class ImportException(Exception):
    pass


class ApiaryLicenceReader():
    '''
    from disturbance.utils.migration_utils import ApiaryLicenceReader
    reader=ApiaryLicenceReader('disturbance/utils/csv/apiary_migration_file_01Sep20211-TEST.csv')
    reader.run_migration()

    ------------------------------------------------------------------------------------------------
    Delete previously migrated proposals/licences:
    for idx, i in enumerate(Proposal.objects.filter(migrated=True)):
        print(idx)
        a = i.approval
        af = a.annual_rental_fees.all()
        if af:
            af.delete()
            
        if i.fee_invoice_references:
            Invoice.objects.filter(reference__in=i.fee_invoice_references).delete()
            
        #i.delete()

    Proposal.objects.filter(migrated=True).delete()
    
    ------------------------------------------------------------------------------------------------
    import pandas as pd
    df=pd.read_excel('/home/jawaidm/Downloads/apiary_migration_file_01Sep2021 - COMPLETED DATA - 26 April 2022 - NOT TO BE REISSUED DATA CHANGE.xlsx')

    df['Start Date']=pd.to_datetime(df['Start Date'], errors='coerce')
    df['Expiry Date']=pd.to_datetime(df['Expiry Date'], errors='coerce')
    df['Issue Date']=pd.to_datetime(df['Issue Date'], errors='coerce')
    df['approval_cpc_date']=pd.to_datetime(df['approval_cpc_date'], errors='coerce')
    df['approval_minister_date']=pd.to_datetime(df['approval_minister_date'], errors='coerce')

    df.iloc[153]
    df.iloc[1]
    df.to_csv('disturbance/utils/csv/apiary_migration_file_26Apr2022_v2.csv', sep=':', index=False)


    ------------------------------------------------------------------------------------------------
    In [147]: df['start_date'] = df['start_date'].fillna(datetime.date.today())

    In [148]: df['expiry_date'] = df['expiry_date'].fillna(datetime.date.today())

    In [149]: df['issue_date'] = df['issue_date'].fillna(df['start_date'])

    # In [150]: df['permit_number']=df['permit_number'].astype('Int32')
    df.loc[df['permit_number'].notnull(), 'permit_number'] = df.loc[df['permit_number'].notnull(), 'permit_number'].apply(int)
    '''
    def __init__(self, filename):
        self.filename = filename
        self.not_found = []
        #self.apiary_licence_lines = self._read_organisation_data()
        self.df = self._read_excel()

        self.application_type = ApplicationType.objects.get(name=ApplicationType.APIARY)
        self.proposal_type = ProposalType.objects.all().order_by('name', '-version').distinct('name').get(name=self.application_type.name)

    def _read_excel(self, filename):
        df = pd.read_excel(filename)

        # Rename the cols from Spreadsheet headers to Model fields names
        df = df.rename(columns=COLUMN_MAPPING)

        # check excel column names are the same column_mappings
        if list(df.columns) != list(COLUMN_MAPPING.values()):
            raise Exception('Column Names have changed!')

        return df

    def run_migration(self):
        with transaction.atomic():
            try:
                #import ipdb; ipdb.set_trace()
                #self._write_to_migrated_apiary_licence_model()
                self._create_licences()
                #self._create_licence_pdf()
                #import denied sites
            except Exception as e:
                print(e)
                import ipdb; ipdb.set_trace()

        try:
            self._create_licence_pdf()
        except Exception as e:
            print(e)
            import ipdb; ipdb.set_trace()


    def _read_organisation_data(self, verify=False):
        lines=[]
        try:
            '''
            Example csv
                address, town/city, state (WA), postcode, org_name, abn, trading_name, first_name, last_name, email, phone_number
                123 Something Road, Perth, WA, 6100, Import Test Org 3, 615503, DDD_03, john, Doe_1, john.doe_1@dbca.wa.gov.au, 08 555 5555

                File No:Licence No:Expiry Date:Term:Trading Name:Licensee:ABN:Title:First Name:Surname:Other Contact:Address 1:Address 2:Address 3:Suburb:State:Country:Post:Telephone1:Telephone2:Mobile:Insurance Expiry:Survey Cert:Name:SPV:ATAP Expiry:Eco Cert Expiry:Vessels:Vehicles:Email1:Email2:Email3:Email4
                2018/0012345-1:HQ12345:28-Feb-21:3 YEAR:MyCompany:MyCompany Pty Ltd::MR:Joe:Any::Po Box 1234:::ESPERANCE:WA:AUSTRALIA:6450:458021841:::23-Jun-18::::30-Jun-18::0:7:any@gmail.com:::
            To test:
                from commercialoperator.components.proposals.models import create_organisation_data
                create_migration_data('commercialoperator/utils/csv/orgs.csv')
            '''
            with open(self.filename) as csvfile:
                reader = csv.reader(csvfile, delimiter=str(':'))
                header = next(reader) # skip header
                #import ipdb; ipdb.set_trace()
                error_lines=[]
                for idx, row in enumerate(reader):
                    #import ipdb; ipdb.set_trace()
                    if row[5].replace(' ','')=='-30.28512637300':
                        import ipdb; ipdb.set_trace()

                    #if idx==3:
                    #    break
                        
                    try:
                        #if not row[0].startswith('#') and row[4].strip().lower() == 'current':
                        if not row[0].startswith('#') or not row[7].strip() == 'AJ & DE Dowsett' or not row[9].replace(' ','') == '':
                            if row[4].startswith('Vacant') and row[9].strip() == '':
                                # Vacant, with no ABN
                                continue

                            data={}
                            data.update({'permit_number': int(row[0].strip().split('.')[0]) if row[0].strip()!='' else None})
                            start_date_raw = row[1].strip()
                            if start_date_raw:
                                #start_date = datetime.datetime.strptime(start_date_raw, '%d/%m/%Y').date()
                                start_date = datetime.datetime.strptime(start_date_raw, '%Y-%m-%d').date()
                                #start_date = datetime.datetime.strptime(start_date_raw, '%Y-%m-%d %H:%M:%S').date()
                                data.update({'start_date': start_date})
                            else:
                                start_date = datetime.date.today()
                                data.update({'start_date': datetime.date.today()})
                                #continue
                            expiry_date_raw = row[2].strip()
                            if expiry_date_raw:
                                expiry_date = datetime.datetime.strptime(row[2].strip(), '%Y-%m-%d').date()
                                #expiry_date = datetime.datetime.strptime(row[2].strip(), '%Y-%m-%d %H:%M:%S').date()
                                data.update({'expiry_date': expiry_date})
                            else:
                                data.update({'expiry_date': datetime.date.today()})

                            try:
                                issue_date = datetime.datetime.strptime(row[3].strip(), '%Y-%m-%d').date()
                                #issue_date = datetime.datetime.strptime(row[3].strip(), '%Y-%m-%d %H:%M:%S').date()
                                data.update({'issue_date': issue_date})
                            # set issue_date to start_date
                            except:
                                data.update({'issue_date': start_date})

                            try:
                                tmp = data['expiry_date']
                            except Exception as e:
                                import ipdb; ipdb.set_trace()

                            data.update({'status': row[4].strip().capitalize()})
                            # JM switched round the below for the csv file provided by Ashlee dated 01Sep2021
                            data.update({'latitude': row[6].translate(string.whitespace)})
                            data.update({'longitude': row[5].translate(string.whitespace)})
                            #data.update({'file_no': row[0].translate(None, string.whitespace)})
                            #data.update({'licence_no': row[1].translate(None, string.whitespace)})
                            #data.update({'expiry_date': row[2].strip()})
                            #data.update({'term': row[3].strip()})


                            data.update({'abn': str(row[9].translate(string.whitespace).replace(' ',''))})
                            data.update({'trading_name': row[7].strip()})
                            if row[8].strip() != '':
                                data.update({'licencee': row[8].strip()})
                            else:
                                # set same as Trading Name
                                #data.update({'licencee': row[7].strip()})
                                data.update({'licencee': row[7].strip() + '(' + data['abn'] + ')'})

                            #data.update({'title': row[10].strip()})
                            first_name_raw = row[10].strip()
                            if first_name_raw:
                                first_name_split = first_name_raw.split('&')
                                data.update({'first_name': first_name_split[0].strip().capitalize()})
                            #data.update({'first_name': row[10].strip().capitalize()})
                            last_name_raw = row[11].strip()
                            if last_name_raw:
                                last_name_split = last_name_raw.split('&')
                                data.update({'last_name': last_name_raw.strip().capitalize()})
                            #data.update({'other_contact': row[12].strip()})
                            #import ipdb; ipdb.set_trace()
                            data.update({'address_line1': row[13].strip()})
                            data.update({'address_line2': row[14].strip()})
                            data.update({'address_line3': row[15].strip()})
                            data.update({'suburb': row[16].strip().capitalize()})
                            data.update({'state': row[17].strip()})

                            country_raw = ' '.join([i.lower().capitalize() for i in row[18].strip().split()])
                            #if country == 'A':
                                #country = 'Australia'
                            country_str = 'Australia' if country_raw.lower().startswith('a') else country_raw
                            try:
                                country=Country.objects.get(printable_name__icontains=country_str)
                            except Exception as e:
                                country=Country.objects.get(iso_3166_1_a2='AU')

                            data.update({'country': country.iso_3166_1_a2}) # 2 char 'AU'
                            if row[19].translate(string.whitespace) != '':
                                data.update({'postcode': str(row[19].translate(string.whitespace).split('.')[0])})
                            else:
                                data.update({'postcode': '6000'})
                            data.update({'phone_number1': row[20].translate(b' -()')})
                            data.update({'phone_number2': row[21].translate(b' -()')})
                            data.update({'mobile_number': row[22].translate(b' -()')})

                            emails = row[23].translate(b' -()').replace(';', ',').split(',')
                            #import ipdb; ipdb.set_trace()
                            if row[24].translate(b' -()').capitalize() == '':
                                # This is a Permit
                                data.update({'licensed_site': False})
                            else:
                                data.update({'licensed_site': True})

                            # batch_no:approval_cpc_date:approval_minister_date:map_ref:forest_block:cog:roadtrack:zone:catchment:dra_permit
                            data.update({'batch_no': row[25].strip()})
                            approval_cpc_date_raw = row[26].strip() if len(row)>26 else ''
                            try:
                                if approval_cpc_date_raw:
                                    approval_cpc_date = datetime.datetime.strptime(approval_cpc_date_raw, '%Y-%m-%d').date()
                                    data.update({'approval_cpc_date': approval_cpc_date})
                                else:
                                    data.update({'approval_cpc_date': None})
                                approval_minister_date_raw = row[27].strip()
                            except Exception as e:
                                print(e)
                                import ipdb; ipdb.set_trace()

                            if approval_minister_date_raw:
                                approval_minister_date = datetime.datetime.strptime(approval_minister_date_raw, '%Y-%m-%d').date()
                                data.update({'approval_minister_date': approval_minister_date})
                            else:
                                data.update({'approval_minister_date': None})
                            data.update({'map_ref': row[28].strip()})
                            data.update({'forest_block': row[29].strip()})
                            data.update({'cog': row[30].strip()})
                            data.update({'roadtrack': row[31].strip()})
                            data.update({'zone': row[32].strip()})
                            data.update({'catchment': row[33].strip()})
                            data.update({'dra_permit': row[34].strip() if row[34].strip() else False})
                            data.update({'site_status': settings.SITE_STATUS_SUSPENDED if row[35].strip() else settings.SITE_STATUS_CURRENT})

                            #pli_expiry_date_raw = row[25].strip()
                            #if pli_expiry_date_raw:
                            #    pli_expiry_date = datetime.datetime.strptime(pli_expiry_date_raw, '%d/%m/%Y').date()
                            #    data.update({'pli_expiry_date': pli_expiry_date})

                            #for num, email in enumerate(emails, 1):
                             #   data.update({'email{}'.format(num): email.lower()})
                            if emails:
                                data.update({'email': emails[0].strip().lower()})
                            # Org or individual record
                            if data.get('licencee')!='' and data.get('abn')!='':
                                data.update({'licencee_type': 'organisation'})
                            #elif not data.get('licencee'):
                            elif data.get('abn')=='':
                                data.update({'licencee_type': 'individual'})
                            else:
                                print("Entry is not a valid organisation or individual licence record")
                                import ipdb; ipdb.set_trace()
                                #raise ImportException("Entry is not a valid organisation or individual licence record")

                            #if data['abn'] != '':
                            lines.append(data) # must be an org
                            ##else:
                            ##   print data['first_name'], data['last_name'], data['email1'], data['abn']
                            ##   print
                    except Exception as e:
                        print(idx)
                        print(e)
                        print(row)
                        error_lines.append(row)
                        print 

        except Exception as e:
            #logger.info('{}'.format(e))
#            if data:
#                logger.error('{}'.format(e))
#                logger.error('Main {}'.format(data))
#                #print('Main {}'.format(data))
#            else:
#                print(e)
            print(e)
            import ipdb; ipdb.set_trace()

        print(len(error_lines))
        return lines

    def _create_individual(self, data, count, debug=False):
        try:
            #if data['email1'] == 'info@safaris.net.au':
            #    import ipdb; ipdb.set_trace()
            first_name = data['first_name'] if 'first_name' in data else 'No First Name'
            last_name = data['last_name'] if 'last_name' in data else 'No Last Name'
            email = data['email'].replace(' ', '')
            user = EmailUser.objects.filter(email=email)
            if len(user) == 0:
                user, created_user = EmailUser.objects.get_or_create(email=email,
                        defaults={'first_name': first_name, 'last_name': last_name, 'phone_number': data['phone_number1'], 'mobile_number': data['mobile_number']}
                    )
            else:
                user = user[0]
            return user
            #print '{} {} {}'.format(data['first_name'], data['last_name'], EmailUser.objects.filter(first_name=data['first_name'], last_name=data['last_name']))
            #print data['email1']
        except Exception:
            #print 'user: {}   *********** 1 *********** FAILED'.format(data['email'])
            logger.error('user: {}   *********** 1 *********** FAILED'.format(data['email']))

    def _create_organisation(self, data, count, debug=False):
        #import ipdb; ipdb.set_trace()
        #created_lo = False
        if debug:
            import ipdb; ipdb.set_trace()
        try:
            #if data['email1'] == 'info@safaris.net.au':
            #    import ipdb; ipdb.set_trace()
            first_name = data['first_name'] if 'first_name' in data else 'No First Name'
            last_name = data['last_name'] if 'last_name' in data else 'No Last Name'
            email = data['email'].replace(' ', '')
            user = EmailUser.objects.filter(email=email)
            if len(user) == 0:
                user, created_user = EmailUser.objects.get_or_create(email=email,
                        defaults={'first_name': first_name, 'last_name': last_name, 'phone_number': data['phone_number1'], 'mobile_number': data['mobile_number']}
                    )
            else:
                user = user[0]
            #print '{} {} {}'.format(data['first_name'], data['last_name'], EmailUser.objects.filter(first_name=data['first_name'], last_name=data['last_name']))
            #print data['email1']
        except Exception:
            print('user: {}   *********** 1 *********** FAILED'.format(data['email']))
            import ipdb; ipdb.set_trace()
            #return

        lo=ledger_organisation.objects.filter(abn=data['abn'])
        if lo.count() > 0:
            lo = lo[0]

            if not lo.postal_address:
                oa, created = OrganisationAddress.objects.get_or_create(
                    line1=data['address_line1'],
                    locality=data['suburb'],
                    postcode=str(data['postcode']) if data['postcode'] else '0000',
                    defaults={
                        'line2': data['address_line2'],
                        'line3': data['address_line3'],
                        'state': data['state'],
                        'country': country.code,
                    }
                )
                lo.postal_address=oa
                lo.save()

        else:
            try:
                #print 'Country: {}'.format(data['country'])
                #country_str = 'Australia' if country_raw.lower().startswith('a') else country_raw
                try:
                    country=Country.objects.get(iso_3166_1_a2=data.get('country'))
                except Exception as e:
                    country=Country.objects.get(iso_3166_1_a2='AU')

                #country=Country.objects.get(printable_name__icontains=data['country'])
                oa, created = OrganisationAddress.objects.get_or_create(
                    line1=data['address_line1'],
                    locality=data['suburb'],
                    postcode=str(data['postcode']) if data['postcode'] else '0000',
                    defaults={
                        'line2': data['address_line2'],
                        'line3': data['address_line3'],
                        'state': data['state'],
                        'country': country.code,
                    }
                )
            except MultipleObjectsReturned:
                oa = OrganisationAddress.objects.filter(
                    line1=data['address_line1'],
                    locality=data['suburb'],
                    postcode=str(data['postcode']) if data['postcode'] else '0000',
                    line2=data['address_line2'],
                    line3=data['address_line3'],
                    state=data['state'],
                    country=country.code
                ).first()

            except Exception as e:
                print('Country 2: {}'.format(data['country']))
                print(e)

                try:
                    lo, created_lo = ledger_organisation.objects.create(
                        abn=data['abn'],
                        name=data['licencee'],
                        postal_address=oa,
                        billing_address=oa,
                        trading_name=data['trading_name'],
                    )
                    org, created_org = Organisation.objects.get_or_create(organisation=lo)
                except Exception as e:
                    import ipdb; ipdb.set_trace()

        abn_existing = []
        abn_new = []
        try:
            lo=ledger_organisation.objects.get(abn=data['abn'])

            for org in lo.organisation_set.all():
                for contact in org.contacts.all():
                    if 'ledger.dpaw.wa.gov.au' in contact.email and data['email'] and org.contacts.filter(email=data['email']).count()==0:
                        contact.email = data['email']
                        contact.save()

            abn_existing.append(data['abn'])
            print('{}, Existing ABN: {}'.format(count, data['abn']))
            process = False
        except Exception as e:
            print('{}, Add ABN: {}'.format(count, data['abn']))
        #print 'DATA: {}'.format(data)

        try:
            try:
                country=Country.objects.get(iso_3166_1_a2=data.get('country'))
            except Exceptioon as e:
                country=Country.objects.get(iso_3166_1_a2='AU')

            oa, created = OrganisationAddress.objects.get_or_create(
                line1=data['address_line1'],
                locality=data['suburb'],
                postcode=data['postcode'] if data['postcode'] else '0000',
                defaults={
                    'line2': data['address_line2'],
                    'line3': data['address_line3'],
                    'state': data['state'],
                    'country': country.code,
                }
            )
        except MultipleObjectsReturned:
            oa = OrganisationAddress.objects.filter(
                line1=data['address_line1'],
                locality=data['suburb'],
                postcode=data['postcode'] if data['postcode'] else '0000',
                line2=data['address_line2'],
                line3=data['address_line3'],
                state=data['state'],
                country=country.code
            ).first()

        except Exception as e:
            print('Country 2: {}'.format(data['country']))
            print(e)
            import ipdb; ipdb.set_trace()

        try:
            #import ipdb; ipdb.set_trace()
            data['licencee'] = data['licencee'] + ' ' if ledger_organisation.objects.filter(name=data['licencee']) else data['licencee']

            try:
                lo = ledger_organisation.objects.get(abn=data['abn'])
            except:
                lo, created_lo = ledger_organisation.objects.get_or_create(
                    abn=data['abn'],
                    defaults={
                        'name': data['licencee'],
                        'postal_address': oa,
                        'billing_address': oa,
                        'trading_name': data['trading_name']
                    }
                )

        except Exception as e:
            print('Error creating Organisation: {} - {}'.format(data['licencee'], data['abn']))
            print(e)
            import ipdb; ipdb.set_trace()

        try:
            org, created = Organisation.objects.get_or_create(organisation=lo)
        except Exception as e:
            print('Error: Org: {}'.format(org))
            print(e)
            import ipdb; ipdb.set_trace()


        #if data['abn']!='38052249024':
        print(f'Ledger_Org: {lo}, {org.delegates.all().count()}')
        if org.delegates.all().count()==0:
            #import ipdb; ipdb.set_trace()
            try:
                delegate, created = UserDelegation.objects.get_or_create(organisation=org, user=user)
            except Exception as e:
                print('Delegate Creation Failed: {}'.format(user))
                import ipdb; ipdb.set_trace()

            try:
                oc, created = OrganisationContact.objects.get_or_create(
                    organisation=org,
                    #email=data['email1'],
                    email=delegate.user.email,
                    defaults={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone_number': user.phone_number,
                        'mobile_number': user.mobile_number if data['mobile_number'] else '',
                        'user_status': 'active',
                        'user_role': 'organisation_admin',
                        'is_admin': True
                    }
                )
                if oc and 'ledger.dpaw.wa.gov.au' in oc.email:
                    oc.email = delegate.user.email
                    oc.save()

                if oc and not created:
                    oc.user_role ='organisation_admin'
                    oc.is_admin = True
                    oc.user_status ='active'
                    oc.save()

            except Exception as e:
                print('Org Contact: {}'.format(user))
                print(e)
                import ipdb; ipdb.set_trace()
                #raise

        #return abn_new, abn_existing
        return org, user


    def _migrate_approval(self, data, submitter, applicant=None, proxy_applicant=None):
        from disturbance.components.approvals.models import Approval
        #import ipdb; ipdb.set_trace()
        try:
            t = time.process_time()
            print('******************************************************** 1: {}'.format(time.process_time() - t)); t = time.process_time()

            if applicant:
                proposal, p_created = Proposal.objects.get_or_create(
                                application_type=self.application_type,
                                activity='Apiary',
                                submitter=submitter,
                                applicant=applicant,
                                schema=self.proposal_type.schema,
                            )
                approval, approval_created = Approval.objects.update_or_create(
                                applicant=applicant,
                                status=Approval.STATUS_CURRENT,
                                apiary_approval=True,
                                defaults = {
                                    'issue_date':data['issue_date'] if not np.nan else datetime.date.today(),
                                    'expiry_date':data['expiry_date'],
                                    'start_date':data['start_date'] if not np.nan else datetime.date.today(),
                                    #'submitter':submitter,
                                    'current_proposal':proposal,
                                    }
                            )
            else:
                import ipdb; ipdb.set_trace()

            if 'PM' not in proposal.lodgement_number:
                proposal.lodgement_number = proposal.lodgement_number.replace('P', 'PM') # Application Migrated
            proposal.approval= approval
            proposal.processing_status='approved'
            proposal.customer_status='approved'
            proposal.migrated=True
            proposal.proposed_issuance_approval = {
                    'start_date': data['start_date'].strftime('%d-%m-%Y'),
                    'expiry_date': data['expiry_date'].strftime('%d-%m-%Y'),
                    'details': 'Migrated',
                    'cc_email': 'Migrated',
            }

            approval.migrated=True

            # create invoice for payment of zero dollars
            order = create_invoice(proposal)
            invoice = Invoice.objects.get(order_number=order.number) 
            proposal.fee_invoice_references = [invoice.reference]

            proposal.save()
            approval.save()

            # create apiary sites and intermediate table entries
            geometry = GEOSGeometry('POINT(' + str(data['latitude']) + ' ' + str(data['longitude']) + ')', srid=4326)
            apiary_site = ApiarySite.objects.create()
            site_category = get_category(geometry)
            intermediary_approval_site = ApiarySiteOnApproval.objects.create(
                                            apiary_site=apiary_site,
                                            approval=approval,
                                            wkb_geometry=geometry,
                                            site_category = site_category,
                                            licensed_site=data['licensed_site'],
                                            batch_no=data['batch_no'],
                                            approval_cpc_date=data['approval_cpc_date'],
                                            approval_minister_date=data['approval_minister_date'],
                                            map_ref=data['map_ref'],
                                            forest_block=data['forest_block'],
                                            cog=data['cog'],
                                            roadtrack=data['roadtrack'],
                                            zone=data['zone'],
                                            catchment=data['catchment'],
                                            dra_permit=data['dra_permit'],
                                            site_status=data['site_status'],
                                            )
            pa, pa_created = ProposalApiary.objects.get_or_create(proposal=proposal)

            intermediary_proposal_site = ApiarySiteOnProposal.objects.create(
                                            apiary_site=apiary_site,
                                            #approval=approval,
                                            proposal_apiary=pa,
                                            wkb_geometry_draft=geometry,
                                            site_category_draft = site_category,
                                            wkb_geometry_processed=geometry,
                                            site_category_processed = site_category,
                                            licensed_site=data['licensed_site'],
                                            batch_no=data['batch_no'],
                                            approval_cpc_date=data['approval_cpc_date'],
                                            approval_minister_date=data['approval_minister_date'],
                                            map_ref=data['map_ref'],
                                            forest_block=data['forest_block'],
                                            cog=data['cog'],
                                            roadtrack=data['roadtrack'],
                                            zone=data['zone'],
                                            catchment=data['catchment'],
                                            dra_permit=data['dra_permit'],
                                            )

            apiary_site.latest_approval_link=intermediary_approval_site
            apiary_site.latest_proposal_link=intermediary_proposal_site
            apiary_site.save()

            print('******************************************************** 6: {}'.format(time.process_time() - t)); t = time.process_time()

        except Exception as e:
            logger.error('{}'.format(e))
            import ipdb; ipdb.set_trace()
            return None

        return approval

    def _create_licences(self):
        count = 1
        #for data in self.apiary_licence_lines:
        for index, data in self.df[:3].iterrows():
            # do not run if row has already been processed in a previous migration
            #if not data.get('previously_migrated'):
                if data.get('licencee_type') == 'organisation':
                    org, submitter = self._create_organisation(data, count)
                    self._migrate_approval(data=data, submitter=submitter, applicant=org, proxy_applicant=None)
                    print("Permit number {} migrated".format(data.get('permit_number')))
                    print
                    print

                elif data.get('licencee_type') == 'individual':
                    user = self._create_individual(data, count)
                    self._migrate_approval(data=data, submitter=user, applicant=None, proxy_applicant=user)
                    print("Permit number {} migrated".format(data.get('permit_number')))

                else:
                    # declined and not to be reissued
                    status = data['status']
            count += 1


    def _create_licence_pdf(self):
        approvals_migrated = Approval.objects.filter(current_proposal__application_type__name=ApplicationType.APIARY, migrated=True)
        print('Total Approvals: {} - {}'.format(approvals_migrated.count(), approvals_migrated))
        for idx, a in enumerate(approvals_migrated):
            a.generate_doc(a.current_proposal.submitter)
            print('{}, Created PDF for Approval {}'.format(idx, a))



def create_invoice(proposal, payment_method='other'):
        """
        This will create and invoice and order from a basket bypassing the session
        and payment bpoint code constraints.
        """
        from ledger.checkout.utils import createCustomBasket
        from ledger.payments.invoice.utils import CreateInvoiceBasket
        from ledger.accounts.models import EmailUser

        now = timezone.now().date()
        line_items = [
            {'ledger_description': 'Migration Licence Charge Waiver - {} - {}'.format(now, proposal.lodgement_number),
             'oracle_code': 'N/A', #proposal.application_type.oracle_code_application,
             'price_incl_tax':  Decimal(0.0),
             'price_excl_tax':  Decimal(0.0),
             'quantity': 1,
            }
        ]

        user = EmailUser.objects.get(email__icontains='das@dbca.wa.gov.au')
        invoice_text = 'Migration Invoice'

        basket  = createCustomBasket(line_items, user, settings.PAYMENT_SYSTEM_ID)
        order = CreateInvoiceBasket(payment_method=payment_method, system=settings.PAYMENT_SYSTEM_PREFIX).create_invoice_and_order(basket, 0, None, None, user=user, invoice_text=invoice_text)

        return order
    

