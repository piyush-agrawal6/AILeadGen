import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {ICPCompare} from '@/components/workspaces/icp-compare';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
beforeEach(()=>vi.resetAllMocks());
it('compares owned saved criteria only on request and presents actual changed fields',async()=>{
 vi.mocked(request).mockResolvedValue({before_revision:1,after_revision:2,changes:{criteria:{before:{company:{industries:['Dentistry'],countries:[]}},after:{company:{industries:['Dentistry'],countries:['United Kingdom']}}}}});
 render(<ICPCompare profileId="owned-profile" revision={2}/>);expect(request).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Compare versions'}));
 expect(await screen.findByRole('status')).toHaveTextContent('1 changed field between versions 1 and 2.');
 expect(screen.getByRole('cell',{name:'United Kingdom'})).toBeVisible();
 expect(screen.queryByRole('cell',{name:'Dentistry'})).not.toBeInTheDocument();
 expect(request).toHaveBeenCalledWith('/organization/icps/owned-profile/compare?before=1&after=2');
});
it('preserves chosen versions on failure and prevents reversed or equal comparisons',async()=>{
 vi.mocked(request).mockRejectedValue(new Error('Saved version is unavailable.'));
 render(<ICPCompare profileId="owned-profile" revision={3}/>);
 fireEvent.change(screen.getByLabelText('Earlier version'),{target:{value:'1'}});
 fireEvent.click(screen.getByRole('button',{name:'Compare versions'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Saved version is unavailable.');
 expect(screen.getByLabelText('Earlier version')).toHaveValue(1);
 fireEvent.change(screen.getByLabelText('Earlier version'),{target:{value:'3'}});
 expect(screen.getByRole('button',{name:'Compare versions'})).toBeDisabled();
});
