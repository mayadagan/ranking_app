# load ranked: 

def load_currently_ranked(doctor_key, basic_doctor_path, iteration_num):

    
    initial_train_pairs_path = basic_doctor_path + f"/{doctor_key}_train_iter_0_ranked.pkl"
    iter_1_train_pairs_path = basic_doctor_path + f"/{doctor_key}_train_iter_1_ranked.json"
    iter_2_train_pairs_path = basic_doctor_path + f"/{doctor_key}_train_iter_2_ranked.json"
    iter_3_train_pairs_path = basic_doctor_path + f"/{doctor_key}_train_iter_3_ranked.json"
    iter_1_train_pairs = []
    iter_2_train_pairs = []
    iter_3_train_pairs = []
    if iteration_num >=0:
        with open(initial_train_pairs_path, "r") as f:
            initial_train_pairs = json.load(f)
    if iteration_num >= 1:    
        # try:
        with open(iter_1_train_pairs_path, "r") as f:
            iter_1_train_pairs = json.load(f)
        # except FileNotFoundError:
        #     iter_1_train_pairs = []
    
    if iteration_num >= 2:    
    # try:
        with open(iter_2_train_pairs_path, "r") as f:
            iter_2_train_pairs = json.load(f)
    # except FileNotFoundError:
    #     iter_2_train_pairs = []

    if iteration_num >= 3:    
    # try:
        with open(iter_3_train_pairs_path, "r") as f:
            iter_3_train_pairs = json.load(f)
    # except FileNotFoundError:
    #     iter_3_train_pairs = []

    all_test_pairs_path = basic_doctor_path + f"/{doctor_key}_test_ranked.pkl"
    part_A_test_pairs_path = basic_doctor_path + f"/{doctor_key}_test_part_A_ranked.pkl"
    part_B_test_pairs_path = basic_doctor_path + f"/{doctor_key}_test_part_B_ranked.json"

    try:
        with open(all_test_pairs_path, "r") as f:
            all_test_pairs = json.load(f)
    except FileNotFoundError:
        try:
            with open(part_A_test_pairs_path, "r") as f:
                part_A_test_pairs = json.load(f)
            with open(part_B_test_pairs_path, "r") as f:
                part_B_test_pairs = json.load(f)  
            all_test_pairs = part_A_test_pairs + part_B_test_pairs
        except FileNotFoundError:
            all_test_pairs = []    
   
        
    all_train_pairs = {doctor_key: initial_train_pairs + iter_1_train_pairs + iter_2_train_pairs + iter_3_train_pairs}
    all_test_pairs = {doctor_key: all_test_pairs}
    print("current ranked train pairs:", len(all_train_pairs[doctor_key]))
    print("current ranked test pairs:", len(all_test_pairs[doctor_key]))
    return all_train_pairs, all_test_pairs

# get next 100 pairs and save them
def get_next_pairs(
    doctor_key,
    basic_doctor_path,
    iteration_num,
    prev_model,
    df_train_scaled,
    all_train_pairs,
    rec_weight_dict,
    num_model,
    model_type,  
    patient_counter,
    doctors_iteration_data,
    group_counter,   
):
    if prev_model is None:
        # load saved model from iter 1
        path_prev_model = basic_doctor_path + f"/{doctor_key}_model_iter_{iteration_num}.pth"
        prev_model = RankNet(input_dim=23, hidden_dim=128)                # you must recreate the model object
        prev_model.load_state_dict(torch.load(path_prev_model))
        prev_model.eval()

    iteration_num += 1

    al_variant = 5
    sampler_mode = "7030"

    ranked_train_pairs = all_train_pairs[doctor_key]
    
    new_candidate_train, patient_counter, group_counter = generate_candidate_pairs(
        ranked_train_pairs,  ## train pairs already ranked 
        prev_model,
        df_train_scaled,
        rec_weight_dict,
        num_child=0,
        num_chain=0,
        num_model=num_new_pairs,
        min_score_diff=0.1,
        model_type="ranknet",  
        df_train=df_train_scaled,
        patient_counter=patient_counter,
        doctors_iteration_data=doctors_iteration_data,
        doctor_name=doctor_key,
        group_counter=group_counter,
        al_variant=al_variant,
        sampler_mode=sampler_mode
    )
    # Ensure we don't relabel existing AL pairs
    new_candidate_train = remove_duplicate_pairs(new_candidate_train, ranked_train_pairs)

    with open(f"{basic_doctor_path}/{doctor_key}_train_pairs_iter_{iteration_num}_for_ranking.json", "w") as f:
        json.dump(new_candidate_train, f)

    with open(f"{basic_doctor_path}/{doctor_key}_patient_counter.pkl", "wb") as f:
        pickle.dump(patient_counter, f)    

    with open(f"{basic_doctor_path}/{doctor_key}_group_counter.pkl", "wb") as f:
        pickle.dump(group_counter, f) 
        
    return new_candidate_train, patient_counter, group_counter, iteration_num

def load_previous_counters(doctor_key, basic_doctor_path):
    with open(f"{basic_doctor_path}/{doctor_key}_group_counter.pkl", "rb") as f:
        group_counter = pickle.load(f)
    with open(f"{basic_doctor_path}/{doctor_key}_patient_counter.pkl", "rb") as f:
        patient_counter = pickle.load(f)
    return group_counter, patient_counter

def load_previous_results(doctor_key, basic_doctor_path, iteration_num):
    pattern = f"{basic_doctor_path}/iter_{iteration_num - 1}_results_{doctor_key}_*.json"
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No files match {pattern}")
        
    
    # pick the most recently modified file
    latest_file = max(files, key=os.path.getmtime)
    
    with open(latest_file, "r") as f:
        results = json.load(f)

    return results['doctors_metrics'], results['doctors_iteration_data']

# physican name 
doctor_key = 'inbar_safra'
num_new_pairs = 100
doctors_metrics.setdefault(doctor_key, {})
doctors_iteration_data.setdefault(doctor_key, {'iteration_all_pairs': []})

patient_counter = Counter()
group_counter   = Counter()

basic_doctor_path = f"/home/mayamak/mayadag_copy_2/refactored_code/physicians_results/{doctor_key}"
Path(basic_doctor_path).mkdir(parents=True, exist_ok=True)
iteration_num = 0 

iteration_num = 2
print(f'current iteration is {iteration_num}')

doctors_metrics, doctors_iteration_data = load_previous_results(doctor_key, basic_doctor_path, iteration_num)
group_counter, patient_counter = load_previous_counters(doctor_key, basic_doctor_path)