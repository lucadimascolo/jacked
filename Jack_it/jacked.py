import numpy as np
import tqdm
from casatasks import tclean, exportfits
import os

####### Own Tools #######
from src.MsManager import *
from src.UnitTransform import *

class Jack:
    def __init__(self, vis, typ, N, spws, fields, band, test = False):
        
        self.test       = test 
        self.seed       = 42
        self.N          = N
        self.vis        = vis
        self.vis_name = (vis.split('/')[-1]).split('.ms')[0] + typ + '_Jacked_seed'+str(self.seed)+'.ms'
                            
        self.typ        = typ
        self.reader     = MsReader(self.vis, self.typ, spws = spws, fields = fields, band = band)
    
        self.reader.ms_copydir = './output/jacked/'

        if not os.path.exists(self.reader.ms_copydir):
            os.makedirs(self.reader.ms_copydir)
    
        self.reader.ms_modelfile = self.reader.ms_copydir + self.reader.ms_file.split('/')[-1]
        self.vis_jacked =  self.reader.ms_copydir + self.vis_name  
                
        if typ =='com07m':
            self.imsize = 256
            self.imcell = '1.50arcsec'
        elif typ =='com12m':
            self.imsize = 256
            self.imcell = '0.15arcsec'
            
    def _loader(self):
        uvdist, UVreal, UVimag, UVwgts, _, _ = self.reader.uvdata_loader()

        self.UVreal = UVreal
        self.UVimag = UVimag
        self.uvdist = uvdist
        self.UVwgts = UVwgts
        
    def _saver(self):
            
        if self.test is not True:
            self.reader.model_to_ms(self.UVreal_jacked + self.UVimag_jacked*1j,
                                    1., 
                                    'replace', 
                                    (self.vis.split('/')[-1]).split('.ms')[0] + self.typ + '_Jacked_seed'+str(self.seed),
                                    self.wgt)
        else:
            self.reader.model_to_ms(self.UVreal + self.UVimag*1j,
                                    1., 
                                    'replace', 
                                    (self.vis.split('/')[-1]).split('.ms')[0] + self.typ + '_Jacked_seed'+str(self.seed),
                                    self.wgt)

    def _stw_manual(self):
                
        bin_frac = 0.001
        bins = np.logspace(np.log10(np.nanmin(self.uvdist)), np.log10(np.nanmax(self.uvdist)), int(bin_frac*len(self.uvdist)))
        self.UVreal_binned = np.zeros(len(bins)-1)
        self.UVimag_binned = np.zeros(len(bins)-1)

        for i in tqdm.tqdm(range(len(bins)-1)):
            maskb =(self.uvdist >= bins[i]) & (self.uvdist < bins[i+1])
            self.UVreal_binned[i] = np.nansum(self.UVreal_jacked[maskb])
            self.UVimag_binned[i] = np.nansum(self.UVimag[maskb])
            
        self.wgt = 1/(np.nanstd(self.UVreal_binned))**2/ bin_frac
    
    def Jack_it(self):
        indexing = np.ones_like(self.UVreal)
        indexing[:len(indexing)//2] = 0

        np.random.seed(self.seed)
        np.random.shuffle(indexing)

        UVreal_jacked = np.copy(self.UVreal)
        UVreal_jacked[indexing.astype(bool)] *= -1.
        self.UVreal_jacked = UVreal_jacked
        
        UVimag_jacked = np.copy(self.UVimag)
        UVimag_jacked[indexing.astype(bool)] *= -1. 
        self.UVimag_jacked = UVimag_jacked        

        self.wgt = None
        # self._stw_manual()
        
    #######################
    ###     Imaging     ###
    #######################
    
    def _deconvolve(self): #normal

        # HD1 stuff
        # --------------------
        tclean(       vis     =   self.vis_jacked.replace('Model_', 'Model_0_'), 
                  imagename   =       self.vis_jacked.replace('.ms','_cube.im'),  
                  niter       =                                               0,
                  # spw         =                                            '25',
                  imsize      =                                     self.imsize, 
                  cell        =                                     self.imcell, 
                  gridder     =                                      'standard', 
                  weighting   =                                       'natural', 
                  specmode    =                                          'cube') 
        
        exportfits(self.vis_jacked.replace('.ms','_cube.im.image'), 
                   self.vis_jacked.replace('.ms','_cube.im.fits'),
                   overwrite=True)  

        image_name = self.vis_jacked.replace('.ms','_cube.im.fits')

        os.system('rm -rf {0}.pb'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.psf'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.model'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.sumwt'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.weight'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.residual'.format(self.vis_jacked.replace('.ms','_cube.im')))
        os.system('rm -rf {0}.image'.format(self.vis_jacked.replace('.ms','_cube.im')))

        # Standard Stuff
        # ----------------------
        
        tclean( vis         =                      self.vis_jacked, 
                imagename   = self.vis_jacked.replace('.ms','.im'),  
                niter       =                                    0, 
                imsize      =                          self.imsize, 
                cell        =                          self.imcell, 
                gridder     =                           'standard', 
                weighting   =                            'natural', 
                specmode    =                               'mfs')     
        
        exportfits(imagename = self.vis_jacked.replace('.ms','.im.image'), 
                   fitsimage = self.vis_jacked.replace('.ms','.im.fits'), 
                   overwrite = True)
        
        os.system('rm -rf {0}.pb'.format(self.vis_jacked.replace('.ms','.im')))
        os.system('rm -rf {0}.psf'.format(self.vis_jacked.replace('.ms','.im')))
        os.system('rm -rf {0}.model'.format(self.vis_jacked.replace('.ms','.im')))
        os.system('rm -rf {0}.sumwt'.format(self.vis_jacked.replace('.ms','.im')))
        os.system('rm -rf {0}.weight'.format(self.vis_jacked.replace('.ms','.im')))
        os.system('rm -rf {0}.residual'.format(self.vis_jacked.replace('.ms','.im')))
        
    def run(self):

        for i in range(0,self.N,1):
            
            self.seed += i

            print('.. Loading in MS')
            self._loader()
            print('.. Jack Knife it')
            self.Jack_it()
            print('.. Saving to MS')
            self._saver()
            print('.. Deconvolve')
            self._image()
                    
            os.system('rm -vf *.last')
            os.system('rm -vf *.log')