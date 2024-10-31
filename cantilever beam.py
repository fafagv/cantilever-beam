from abaqus import *
from abaqusConstants import *
from caeModules import *
import regionToolset
import mesh
import job
import visualization
import xyPlot
import displayGroupOdbToolset as dgo

# Parameters
beam_length = 5.0 # meters
beam_thickness = 10e-3 # meters
force_magnitude = 1000.0 # Newtons
modulus_of_elasticity = 210e9 # Pascals
poissons_ratio = 0.3
mesh_sizes = [0.2, 0.1, 0.05, 0.02] # meters, example mesh sizes for convergence study

# Create model and part
mdb.models.changeKey(fromName='Model-1', toName='BeamModel')
model = mdb.models['BeamModel']
beam_sketch = model.ConstrainedSketch(name='BeamSketch', sheetSize=10.0)
beam_sketch.rectangle(point1=(0, 0), point2=(beam_length, beam_thickness))
beam_part = model.Part(name='Beam', dimensionality=THREE_D, type=DEFORMABLE_BODY)
beam_part.BaseSolidExtrude(sketch=beam_sketch, depth=1.0)

# Define material
material = model.Material(name='Steel')
material.Elastic(table=((modulus_of_elasticity, poissons_ratio),))

# Section and assign section to part
model.HomogeneousSolidSection(name='BeamSection', material='Steel', thickness=None)
beam_region = (beam_part.cells,)
beam_part.SectionAssignment(region=beam_region, sectionName='BeamSection')

# Create assembly
assembly = model.rootAssembly
assembly.Instance(name='BeamInstance', part=beam_part, dependent=ON)

# Apply boundary conditions
end_face = assembly.instances['BeamInstance'].faces.findAt(((0.0, beam_thickness / 2, 0.5),))
model.DisplacementBC(name='FixedEnd', createStepName='Initial', region=regionToolset.Region(faces=end_face),
                     u1=0.0, u2=0.0, u3=0.0, ur1=0.0, ur2=0.0, ur3=0.0)

# Apply load
load_face1 = assembly.instances['BeamInstance'].faces.findAt(((5 - 1.0, beam_thickness / 2, 0.5),))
load_face2 = assembly.instances['BeamInstance'].faces.findAt(((5 + 1.0, beam_thickness / 2, 0.5),))
model.ConcentratedForce(name='Load1', createStepName='Initial', region=regionToolset.Region(faces=load_face1),
                        cf2=-force_magnitude)
model.ConcentratedForce(name='Load2', createStepName='Initial', region=regionToolset.Region(faces=load_face2),
                        cf2=-force_magnitude)

# Mesh the part with different mesh sizes and run simulations
stress_results = []
for mesh_size in mesh_sizes:
    beam_part.seedPart(size=mesh_size, deviationFactor=0.1, minSizeFactor=0.1)
    beam_part.generateMesh()

    # Create job and submit
    job_name = 'BeamAnalysis_mesh_' + str(mesh_size)
    job = mdb.Job(name=job_name, model='BeamModel', type=ANALYSIS)
    job.submit()
    job.waitForCompletion()

    # Open output database and extract results
    odb_path = job_name + '.odb'
    odb = visualization.openOdb(path=odb_path)
    last_frame = odb.steps['Initial'].frames[-1]

    # Extract stress and displacement values for comparison
    stress_field = last_frame.fieldOutputs['S']
    displacement_field = last_frame.fieldOutputs['U']

    # Get maximum stress and displacement
    max_stress = max(stress.mises for stress in stress_field.values)
    max_displacement = max(disp.magnitude for disp in displacement_field.values)
    
    stress_results.append((mesh_size, max_stress))

    # Close the ODB
    odb.close()

# Plot stress vs mesh size for verification of stress independence
import matplotlib.pyplot as plt

mesh_sizes, stresses = zip(*stress_results)
plt.plot(mesh_sizes, stresses, marker='o')
plt.xlabel('Mesh Size (m)')
plt.ylabel('Stress (Pa)')
plt.title('Stress vs Mesh Size')
plt.grid()
plt.show()
